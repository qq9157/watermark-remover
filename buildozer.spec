[app]

# 应用名称
title = 水印去除

# 包名
package.name = watermarkremover

# 包域名
package.domain = org.watermark

# 源代码目录
source.dir = .
source.include_exts = py,png,jpg,kv,atlas

# 版本
version = 1.0.0

# 应用描述
requirements = python3,kivy,opencv,numpy,pillow,plyer

# 权限
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,CAMERA

# API版本
android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 31

# 架构
android.archs = arm64-v8a,armeabi-v7a

# 图标
# icon.filename = icon.png

# 横屏
orientation = portrait

# 全屏
fullscreen = 0

# Android entry point
android.entrypoint = org.kivy.android.PythonActivity

# 启动画面
# presplash.filename = presplash.png

# 允许备份
android.allow_backup = True

# 主题
android.theme = "@android:style/Theme.Translucent.NoTitleBar"
