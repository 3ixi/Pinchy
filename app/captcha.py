"""
验证码生成功能
"""
import random
import io
import base64
from PIL import Image, ImageDraw, ImageFont
from typing import Tuple

class CaptchaGenerator:
    """验证码生成器"""
    
    def __init__(self, width: int = 120, height: int = 40):
        self.width = width
        self.height = height
        self.font_size = 20
        
    def generate_math_expression(self) -> Tuple[str, int]:
        """生成数学表达式和答案"""
        # 生成两个1-20之间的数字
        num1 = random.randint(1, 20)
        num2 = random.randint(1, 20)
        
        # 随机选择运算符
        operators = ['+', '-', '*']
        operator = random.choice(operators)
        
        if operator == '+':
            answer = num1 + num2
            expression = f"{num1}+{num2}=?"
        elif operator == '-':
            # 确保结果为正数
            if num1 < num2:
                num1, num2 = num2, num1
            answer = num1 - num2
            expression = f"{num1}-{num2}=?"
        else:  # operator == '*'
            # 限制乘法结果在100以内
            num1 = random.randint(1, 10)
            num2 = random.randint(1, 10)
            answer = num1 * num2
            expression = f"{num1}*{num2}=?"
            
        return expression, answer
    
    def generate_captcha_image(self, text: str) -> str:
        """生成验证码图片，返回base64编码的图片"""
        # 创建图片
        image = Image.new('RGB', (self.width, self.height), color='white')
        draw = ImageDraw.Draw(image)
        
        # 尝试使用系统字体，如果失败则使用默认字体
        try:
            # Windows系统字体
            font = ImageFont.truetype("arial.ttf", self.font_size)
        except:
            try:
                # Linux系统字体
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", self.font_size)
            except:
                # 使用默认字体
                font = ImageFont.load_default()
        
        # 计算文本位置
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        x = (self.width - text_width) // 2
        y = (self.height - text_height) // 2
        
        # 绘制文本
        draw.text((x, y), text, fill='black', font=font)
        
        # 添加干扰线
        for _ in range(3):
            x1 = random.randint(0, self.width)
            y1 = random.randint(0, self.height)
            x2 = random.randint(0, self.width)
            y2 = random.randint(0, self.height)
            draw.line([(x1, y1), (x2, y2)], fill='gray', width=1)
        
        # 添加干扰点
        for _ in range(20):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            draw.point((x, y), fill='gray')
        
        # 转换为base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{image_base64}"
    
    def generate(self) -> Tuple[str, int, str]:
        """生成完整的验证码信息"""
        expression, answer = self.generate_math_expression()
        image_data = self.generate_captcha_image(expression)
        return expression, answer, image_data
