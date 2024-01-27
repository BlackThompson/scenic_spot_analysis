import base64
import requests
import api_info
import pandas as pd
import os
from typing import Literal
from openai import OpenAI


# 第一层认知
# Function to encode the image
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def infer_single_img(image_path, save_path, api_key):
    # Getting the base64 string
    base64_image = encode_image(image_path)

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请根据上传的照片，用简洁精炼的语言，描述其中的景色特点。包括但不限于以下方面：\n\
                                    - 自然环境（如山脉、河流、森林、沙滩等)\n\
                                    - 人为元素（如建筑、道路、桥梁等）\n\
                                    - 任何显著的特色或细节。",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        "max_tokens": 500,
    }

    print("正在推理，请稍等...")

    response = requests.post(
        "https://api.openai.com/v1/chat/completions", headers=headers, json=payload
    )

    print("推理完成！")

    with open(save_path, "w", encoding="utf-8-sig") as f:
        f.write(response.json()["choices"][0]["message"]["content"])

    print(f"保存到{save_path}成功！")


# 第二层认知
def get_post_text(index, csv_path):
    df = pd.read_csv(csv_path)
    return df.iloc[index, 1]


def get_post_img_infer(spot_pic_dir):
    """
    得到一个post的所有img的推理结果。并综合
    """
    # index是文件夹的序号，从0开始
    # base_dir = os.path.join(spot_pic_dir, str(index))
    base_dir = spot_pic_dir
    all_infer = ""
    # 遍历base_dir下的所有的txt文件
    for file in os.listdir(base_dir):
        if file.endswith(".txt"):
            txt_path = os.path.join(base_dir, file)
            with open(txt_path, "r", encoding="utf-8-sig") as f:
                post_text = f.read()
                # print(post_text)
                post_text = post_text + "\n"
                all_infer = all_infer + post_text
    # print(all_infer)
    return all_infer


# 起决定作用的函数，决定是否输入图片、文字、或者两者都输入
def get_pic_and_text(
    index, spot_pic_dir, csv_path, use: str = Literal["pic", "text", "both"]
):
    post_all_img_infer = get_post_img_infer(spot_pic_dir)
    post_text = get_post_text(index, csv_path)
    # 如果post_text不是字符串，则设置为空字符串
    if type(post_text) != str:
        post_text = ""

    if use == "pic":
        return post_all_img_infer
    elif use == "text":
        return post_text
    elif use == "both":
        return post_all_img_infer + "\n" + post_text
    else:
        raise ValueError("use参数只能是pic、text或both！")


def infer_single_post(all_infer, api_key, organization, save_path, index):
    try:
        df = pd.read_excel(save_path)
    except:
        df = pd.DataFrame(columns=["description"])

    # 如果index已经存在，就不再重复推理
    if index in df.index:
        print(f"index={index}已经存在，不再重复推理！")
        return

    client = OpenAI(api_key=api_key, organization=organization)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": "根据提供的景点描述，请分析并列出以下三个方面的信息：\n\
                            - 优点：列出该景点的主要优点。\n\
                            - 缺点：指出该景点可能存在的缺点。\n\
                            - 适合的活动：基于景点的特性以及提供的描述，推荐一些适合在此进行的活动。\n\
                            请分点作答，不要多于200字",
            },
            {
                "role": "user",
                "content": all_infer,
            },
        ],
    )
    # print(response.choices[0].message.content)

    new_row = {"description": response.choices[0].message.content}
    df.loc[len(df)] = new_row
    df.to_excel(save_path, index=False)
    print(f"保存到{save_path}成功！")


# 第3层认知
def get_all_post_infer(excel_path):
    df = pd.read_excel(excel_path)
    all_posts_infer = ""
    for i in range(len(df)):
        all_posts_infer = all_posts_infer + df.loc[i, "description"] + "\n"
    return all_posts_infer


def infer_all_posts(all_posts_infer, api_key, organization, save_path):
    client = OpenAI(api_key=api_key, organization=organization)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": "根据提供的关于某个景点的大量描述，请帮我总结并简洁地列出该景点的主要特点。请分为以下四部分：\n\
                            - 景色特点：描述该景点的主要特点。\n\
                            - 优点总结：基于提供的信息，总结出该景点的主要优点。\n\
                            - 缺点总结：从提供的描述中提炼出该景点的主要缺点。\n\
                            - 适合的活动：综合考虑景点的特点，列出几个最适合在此进行的活动项目。\n\
                            请确保每部分的总结全面，便于快速理解该景点的特色，每个部分分点作答。\n",
            },
            {
                "role": "user",
                "content": all_posts_infer,
            },
        ],
    )
    # 判断save_path是否存在，如果不存在则创建，该文件是txt文件
    with open(save_path, "w", encoding="utf-8-sig") as f:
        f.write(response.choices[0].message.content)
    print(f"保存到{save_path}成功！")
