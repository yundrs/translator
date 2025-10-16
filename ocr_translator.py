import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import requests
import base64
import hashlib
import time
import uuid
import json
import os

# 有道 API 配置（用户需替换为实际值）
YOUDAO_OCR_URL = 'https://openapi.youdao.com/ocrapi'
YOUDAO_TRANSLATE_URL = 'https://openapi.youdao.com/api'
APP_KEY = '0132dd473eb9f867'  # 替换为你的有道应用ID
APP_SECRET = 'zFeRKbVYdiSxMJO2IjkkJntpfI1sI9yQ'  # 替换为你的有道应用密钥

# 有道翻译支持的语言代码（从文档提取，支持自动检测源语言）
SUPPORTED_LANGUAGES = {
    'English (en)': 'en',
    'Chinese Simplified (zh-CHS)': 'zh-CHS',
    'Chinese Traditional (zh-CHT)': 'zh-CHT',
    'French (fr)': 'fr',
    'German (de)': 'de',
    'Spanish (es)': 'es',
    'Japanese (ja)': 'ja',
    'Korean (ko)': 'ko',
    'Russian (ru)': 'ru',
    'Italian (it)': 'it',
    'Portuguese (pt)': 'pt',
    'Dutch (nl)': 'nl',
    'Arabic (ar)': 'ar',
    'Hindi (hi)': 'hi',
    'Indonesian (id)': 'id',
    'Thai (th)': 'th',
    'Vietnamese (vi)': 'vi',
}

def truncate(q):
    if q is None:
        return None
    size = len(q)
    return q if size <= 20 else q[:10] + str(size) + q[size-10:]

def encrypt(signStr):
    hash_algorithm = hashlib.sha256()
    hash_algorithm.update(signStr.encode('utf-8'))
    return hash_algorithm.hexdigest()

def extract_text_from_image(image_path):
    try:
        file_size = os.path.getsize(image_path) / (1024 * 1024)  # MB
        if file_size > 2:
            raise ValueError("图像大小超过 2MB 限制。")

        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')

        data = {
            'detectType': '10012',
            'imageType': '1',
            'langType': 'auto',
            'img': img_data,
            'docType': 'json',
            'signType': 'v3',
            'curtime': str(int(time.time())),
            'appKey': APP_KEY,
            'salt': str(uuid.uuid1()),
        }
        signStr = APP_KEY + truncate(img_data) + data['salt'] + data['curtime'] + APP_SECRET
        data['sign'] = encrypt(signStr)

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(YOUDAO_OCR_URL, data=data, headers=headers)
        response.raise_for_status()
        result = response.json()

        if 'errorCode' in result and result['errorCode'] == '0':
            lines = result.get('Result', {}).get('regions', [])
            extracted_text = ''
            for line in lines:
                for word in line.get('lines', []):
                    extracted_text += word.get('text', '') + '\n'
            return extracted_text.strip()
        else:
            raise ValueError(f"有道 OCR API 错误: {result.get('errorCode', '未知错误')}")
    except Exception as e:
        raise ValueError(f"提取文字错误: {e}")

def translate_text_youdao(text, dest_lang):
    if len(text) > 5000:
        text = text[:5000]
        messagebox.showwarning("警告", "文本长度超过 5000 字符，已截断。")

    try:
        data = {
            'from': 'auto',
            'to': dest_lang,
            'signType': 'v3',
            'curtime': str(int(time.time())),
            'appKey': APP_KEY,
            'q': text,
            'salt': str(uuid.uuid1()),
        }
        signStr = APP_KEY + truncate(text) + data['salt'] + data['curtime'] + APP_SECRET
        data['sign'] = encrypt(signStr)

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        response = requests.post(YOUDAO_TRANSLATE_URL, data=data, headers=headers)
        response.raise_for_status()
        result = response.json()

        if 'errorCode' in result and result['errorCode'] == '0':
            return result['translation'][0]
        else:
            raise ValueError(f"有道翻译 API 错误: {result.get('errorCode', '未知错误')}")
    except Exception as e:
        raise ValueError(f"翻译错误: {e}")

class OCRTranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("图像文字识别与翻译工具")
        self.root.geometry("600x500")
        self.root.configure(bg="#f0f0f0")

        self.image_path = None
        self.extracted_text = None
        self.translated_text = None

        # 样式
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 12), padding=10)
        style.configure("TLabel", font=("Arial", 12), background="#f0f0f0")
        style.configure("TCombobox", font=("Arial", 12))

        # 上传按钮
        self.upload_btn = ttk.Button(root, text="上传图片 (PNG/JPG)", command=self.upload_image)
        self.upload_btn.pack(pady=20)

        # 识别按钮
        self.recognize_btn = ttk.Button(root, text="识别图像文字", command=self.recognize_text, state=tk.DISABLED)
        self.recognize_btn.pack(pady=10)

        # 文字输出区域
        self.text_label = ttk.Label(root, text="识别/翻译结果：")
        self.text_label.pack(pady=10)
        self.text_output = tk.Text(root, height=10, width=60, font=("Arial", 10), wrap=tk.WORD)
        self.text_output.pack(pady=10)
        self.text_output.config(state=tk.DISABLED)

        # 保存按钮
        self.save_btn = ttk.Button(root, text="保存当前文字到文件", command=self.save_text, state=tk.DISABLED)
        self.save_btn.pack(pady=10)

        # 翻译区域
        self.translate_frame = tk.Frame(root, bg="#f0f0f0")
        self.translate_frame.pack(pady=10)
        self.translate_label = ttk.Label(self.translate_frame, text="翻译到：")
        self.translate_label.pack(side=tk.LEFT, padx=5)
        self.lang_combo = ttk.Combobox(self.translate_frame, values=list(SUPPORTED_LANGUAGES.keys()), state="readonly")
        self.lang_combo.pack(side=tk.LEFT, padx=5)
        self.translate_btn = ttk.Button(self.translate_frame, text="翻译", command=self.translate_text, state=tk.DISABLED)
        self.translate_btn.pack(side=tk.LEFT, padx=5)

    def upload_image(self):
        try:
            # 调整 filetypes 格式，避免 macOS Tkinter 错误
            file_path = filedialog.askopenfilename(
                filetypes=[
                    ("PNG files", "*.png"),
                    ("JPG files", "*.jpg"),
                    ("JPEG files", "*.jpeg")
                ]
            )
            if file_path:
                ext = os.path.splitext(file_path)[1].lower()
                if ext not in ['.png', '.jpg', '.jpeg']:
                    messagebox.showerror("错误", "仅支持 PNG 或 JPG 格式。")
                    return
                self.image_path = file_path
                messagebox.showinfo("成功", f"图片上传成功：{os.path.basename(file_path)}")
                self.recognize_btn.config(state=tk.NORMAL)
            else:
                messagebox.showinfo("提示", "未选择文件。")
        except Exception as e:
            messagebox.showerror("错误", f"上传文件失败: {str(e)}")

    def recognize_text(self):
        if not self.image_path:
            messagebox.showerror("错误", "请先上传图片。")
            return
        try:
            self.extracted_text = extract_text_from_image(self.image_path)
            self.text_output.config(state=tk.NORMAL)
            self.text_output.delete(1.0, tk.END)
            self.text_output.insert(tk.END, self.extracted_text)
            self.text_output.config(state=tk.DISABLED)
            self.save_btn.config(state=tk.NORMAL)
            self.translate_btn.config(state=tk.NORMAL)
            self.translated_text = None
        except ValueError as ve:
            messagebox.showerror("错误", str(ve))

    def translate_text(self):
        if not self.extracted_text:
            messagebox.showerror("错误", "请先识别文字。")
            return
        selected_lang = self.lang_combo.get()
        if not selected_lang:
            messagebox.showerror("错误", "请选择目标语言。")
            return
        dest_lang = SUPPORTED_LANGUAGES[selected_lang]
        try:
            self.translated_text = translate_text_youdao(self.extracted_text, dest_lang)
            self.text_output.config(state=tk.NORMAL)
            self.text_output.delete(1.0, tk.END)
            self.text_output.insert(tk.END, self.translated_text)
            self.text_output.config(state=tk.DISABLED)
            self.save_btn.config(state=tk.NORMAL)
        except ValueError as ve:
            messagebox.showerror("错误", str(ve))

    def save_text(self):
        if self.translated_text:
            text_to_save = self.translated_text
            default_name = "translated_text.txt"
        elif self.extracted_text:
            text_to_save = self.extracted_text
            default_name = "extracted_text.txt"
        else:
            messagebox.showerror("错误", "没有文字可保存。")
            return

        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt")],
                initialfile=default_name
            )
            if file_path:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(text_to_save)
                messagebox.showinfo("成功", "文字保存成功！")
        except Exception as e:
            messagebox.showerror("错误", f"保存文件失败: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = OCRTranslatorApp(root)
    root.mainloop()