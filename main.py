#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
水印去除软件 - Android版
基于 Kivy + OpenCV 实现
"""

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle, Line
from kivy.core.image import Image as CoreImage
from kivy.metrics import dp
from kivy.clock import Clock

import cv2
import numpy as np
from PIL import Image as PILImage
import io
import os


class SelectionBox(BoxLayout):
    """选择框控件"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = dp(40)
        
        self.label = Label(text='', size_hint_x=0.7, halign='left')
        self.btn_remove = Button(text='×', size_hint_x=0.15, font_size=dp(20))
        self.add_widget(self.label)
        self.add_widget(self.btn_remove)


class ImageCanvas(FloatLayout):
    """支持框选的图像画布"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.image_widget = None
        self.selections = []
        self.current_selection = None
        self.start_pos = None
        self.drawing = False
        
        # 绑定触摸事件
        self.bind(on_touch_down=self.on_touch_down)
        self.bind(on_touch_move=self.on_touch_move)
        self.bind(on_touch_up=self.on_touch_up)
    
    def load_image(self, texture):
        """加载图片"""
        self.clear_widgets()
        self.selections = []
        self.current_selection = None
        
        self.image_widget = Image(texture=texture, 
                                   size_hint=(1, 1),
                                   pos_hint={'center_x': 0.5, 'center_y': 0.5},
                                   allow_stretch=True,
                                   keep_ratio=True)
        self.add_widget(self.image_widget)
    
    def on_touch_down(self, instance, touch):
        if not self.image_widget or not self.collide_point(*touch.pos):
            return False
        
        # 检查触摸是否在图片范围内
        img_pos = self.image_widget.pos
        img_size = self.image_widget.size
        
        if (img_pos[0] <= touch.x <= img_pos[0] + img_size[0] and
            img_pos[1] <= touch.y <= img_pos[1] + img_size[1]):
            self.drawing = True
            self.start_pos = touch.pos
            return True
        return False
    
    def on_touch_move(self, instance, touch):
        if not self.drawing or not self.start_pos:
            return False
        
        # 更新选择框
        if self.current_selection:
            self.canvas.remove(self.current_selection)
        
        with self.canvas:
            Color(1, 0.3, 0.3, 0.5)
            x1, y1 = self.start_pos
            x2, y2 = touch.pos
            self.current_selection = Rectangle(
                pos=(min(x1, x2), min(y1, y2)),
                size=(abs(x2 - x1), abs(y2 - y1))
            )
        return True
    
    def on_touch_up(self, instance, touch):
        if not self.drawing:
            return False
        
        self.drawing = False
        
        if self.current_selection and self.start_pos:
            # 计算选择区域（相对于图片的位置）
            img_pos = self.image_widget.pos
            img_size = self.image_widget.size
            
            x1, y1 = self.start_pos
            x2, y2 = touch.pos
            
            # 转换为图片坐标
            rel_x1 = (min(x1, x2) - img_pos[0]) / img_size[0]
            rel_y1 = (min(y1, y2) - img_pos[1]) / img_size[1]
            rel_x2 = (max(x1, x2) - img_pos[0]) / img_size[0]
            rel_y2 = (max(y1, y2) - img_pos[1]) / img_size[1]
            
            if abs(rel_x2 - rel_x1) > 0.02 and abs(rel_y2 - rel_y1) > 0.02:
                self.selections.append({
                    'rel_x1': rel_x1, 'rel_y1': rel_y1,
                    'rel_x2': rel_x2, 'rel_y2': rel_y2
                })
        
        self.start_pos = None
        if self.current_selection:
            self.canvas.remove(self.current_selection)
            self.current_selection = None
        
        return True
    
    def clear_selections(self):
        """清除所有选择"""
        self.selections = []
        self.canvas.clear()
    
    def get_selections_in_image_coords(self, img_width, img_height):
        """获取图片坐标系下的选择区域"""
        result = []
        for sel in self.selections:
            result.append({
                'x1': int(sel['rel_x1'] * img_width),
                'y1': int((1 - sel['rel_y2']) * img_height),  # Y轴翻转
                'x2': int(sel['rel_x2'] * img_width),
                'y2': int((1 - sel['rel_y1']) * img_height)
            })
        return result


class WatermarkRemoverApp(App):
    """水印去除应用"""
    
    def build(self):
        self.title = '水印去除'
        self.original_image = None
        self.original_texture = None
        self.result_image = None
        self.image_path = None
        
        # 主布局
        main_layout = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(10))
        
        # 顶部标题
        title = Label(text='💧 水印去除软件', 
                      size_hint_y=None, height=dp(50),
                      font_size=dp(24), bold=True,
                      color=(0.4, 0.5, 0.9, 1))
        main_layout.add_widget(title)
        
        # 图像画布
        self.image_canvas = ImageCanvas(size_hint=(1, 0.55))
        main_layout.add_widget(self.image_canvas)
        
        # 选择计数
        self.selection_label = Label(text='已选择 0 个区域', 
                                     size_hint_y=None, height=dp(30),
                                     font_size=dp(14),
                                     color=(0.4, 0.5, 0.9, 1))
        main_layout.add_widget(self.selection_label)
        
        # 控制面板
        control_panel = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(200), spacing=dp(8))
        
        # 算法选择
        algo_layout = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
        algo_layout.add_widget(Label(text='算法:', size_hint_x=0.25, font_size=dp(14)))
        self.algo_spinner = Spinner(
            text='TELEA (快速)',
            values=['TELEA (快速)', 'NS (高质量)'],
            size_hint_x=0.75,
            font_size=dp(14)
        )
        algo_layout.add_widget(self.algo_spinner)
        control_panel.add_widget(algo_layout)
        
        # 修复半径
        radius_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        radius_layout.add_widget(Label(text='半径:', size_hint_x=0.2, font_size=dp(14)))
        self.radius_slider = Slider(min=1, max=15, value=5, size_hint_x=0.6)
        self.radius_label = Label(text='5', size_hint_x=0.2, font_size=dp(16), bold=True)
        self.radius_slider.bind(value=lambda inst, val: setattr(self.radius_label, 'text', str(int(val))))
        radius_layout.add_widget(self.radius_slider)
        radius_layout.add_widget(self.radius_label)
        control_panel.add_widget(radius_layout)
        
        # 按钮行
        btn_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        
        self.btn_select = Button(text='📷 选图', font_size=dp(16))
        self.btn_select.bind(on_press=self.select_image)
        btn_layout.add_widget(self.btn_select)
        
        self.btn_clear = Button(text='🗑️ 清除', font_size=dp(16))
        self.btn_clear.bind(on_press=self.clear_selections)
        btn_layout.add_widget(self.btn_clear)
        
        control_panel.add_widget(btn_layout)
        
        # 处理按钮
        self.btn_process = Button(text='🚀 开始去除水印', 
                                  size_hint_y=None, height=dp(50),
                                  font_size=dp(18),
                                  background_color=(0.4, 0.5, 0.9, 1),
                                  disabled=True)
        self.btn_process.bind(on_press=self.process_image)
        control_panel.add_widget(self.btn_process)
        
        main_layout.add_widget(control_panel)
        
        # 保存按钮（初始隐藏）
        self.btn_save = Button(text='💾 保存结果', 
                               size_hint_y=None, height=dp(50),
                               font_size=dp(16),
                               background_color=(0.3, 0.8, 0.5, 1),
                               disabled=True)
        self.btn_save.bind(on_press=self.save_result)
        main_layout.add_widget(self.btn_save)
        
        return main_layout
    
    def select_image(self, instance):
        """选择图片"""
        from plyer import filechooser
        
        try:
            filechooser.open_file(
                title='选择图片',
                filters=[('图片文件', '*.jpg', '*.jpeg', '*.png', '*.bmp')],
                on_selection=self.on_image_selected
            )
        except Exception as e:
            self.show_message('提示', f'请授予存储权限\n{str(e)}')
    
    def on_image_selected(self, selection):
        """图片选择回调"""
        if not selection:
            return
        
        self.image_path = selection[0]
        
        try:
            # 读取图片
            self.original_image = cv2.imread(self.image_path)
            if self.original_image is None:
                self.show_message('错误', '无法读取图片')
                return
            
            # 转换为纹理
            self.original_texture = self.cv2_to_texture(self.original_image)
            self.image_canvas.load_image(self.original_texture)
            
            self.btn_process.disabled = False
            self.btn_save.disabled = True
            self.result_image = None
            
            self.show_message('成功', f'已加载图片\n{os.path.basename(self.image_path)}')
            
        except Exception as e:
            self.show_message('错误', f'加载失败: {str(e)}')
    
    def cv2_to_texture(self, cv_image):
        """OpenCV图像转Kivy纹理"""
        # BGR转RGB
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        
        # 旋转90度（因为Kivy坐标系不同）
        rgb_image = np.rot90(rgb_image)
        
        # 转换为纹理
        from kivy.graphics.texture import Texture
        h, w = rgb_image.shape[:2]
        texture = Texture.create(size=(w, h))
        texture.blit_buffer(rgb_image.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        
        return texture
    
    def clear_selections(self, instance):
        """清除选择"""
        self.image_canvas.clear_selections()
        self.selection_label.text = '已选择 0 个区域'
    
    def process_image(self, instance):
        """处理图片"""
        if self.original_image is None:
            self.show_message('提示', '请先选择图片')
            return
        
        selections = self.image_canvas.get_selections_in_image_coords(
            self.original_image.shape[1], 
            self.original_image.shape[0]
        )
        
        if not selections:
            self.show_message('提示', '请在图片上框选水印区域')
            return
        
        # 显示处理中
        self.btn_process.text = '⏳ 处理中...'
        self.btn_process.disabled = True
        
        # 使用Clock延迟执行，让UI更新
        Clock.schedule_once(lambda dt: self._do_process(selections), 0.1)
    
    def _do_process(self, selections):
        """执行处理"""
        try:
            # 获取参数
            algorithm = cv2.INPAINT_TELEA if 'TELEA' in self.algo_spinner.text else cv2.INPAINT_NS
            radius = int(self.radius_slider.value)
            
            # 创建掩码
            mask = np.zeros(self.original_image.shape[:2], dtype=np.uint8)
            for sel in selections:
                cv2.rectangle(mask, 
                             (sel['x1'], sel['y1']), 
                             (sel['x2'], sel['y2']), 
                             255, -1)
            
            # 执行修复
            self.result_image = cv2.inpaint(self.original_image, mask, radius, algorithm)
            
            # 显示结果
            result_texture = self.cv2_to_texture(self.result_image)
            self.image_canvas.load_image(result_texture)
            
            self.btn_save.disabled = False
            self.show_message('完成', '水印去除完成！\n点击"保存结果"保存图片')
            
        except Exception as e:
            self.show_message('错误', f'处理失败: {str(e)}')
        
        self.btn_process.text = '🚀 开始去除水印'
        self.btn_process.disabled = False
    
    def save_result(self, instance):
        """保存结果"""
        if self.result_image is None:
            return
        
        try:
            from plyer import storagepath
            
            # 获取下载目录
            download_dir = storagepath.get_downloads_dir()
            if not download_dir:
                download_dir = '/sdcard/Download'
            
            # 生成文件名
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'watermark_removed_{timestamp}.png'
            filepath = os.path.join(download_dir, filename)
            
            # 保存
            cv2.imwrite(filepath, self.result_image)
            
            self.show_message('保存成功', f'图片已保存到:\n{filepath}')
            
        except Exception as e:
            self.show_message('错误', f'保存失败: {str(e)}')
    
    def show_message(self, title, message):
        """显示消息弹窗"""
        content = BoxLayout(orientation='vertical', padding=dp(20), spacing=dp(10))
        content.add_widget(Label(text=message, font_size=dp(16)))
        
        btn = Button(text='确定', size_hint_y=None, height=dp(50), font_size=dp(16))
        content.add_widget(btn)
        
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.4))
        btn.bind(on_press=popup.dismiss)
        popup.open()


if __name__ == '__main__':
    WatermarkRemoverApp().run()
