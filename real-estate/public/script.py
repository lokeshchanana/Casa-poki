from PIL import Image
img = Image.open('/public/lc-logo.png').convert('RGBA')
bg = Image.new('RGBA', img.size, '#1F2933')
bg.paste(img, (0, 0), img)
bg.thumbnail((256, 256))
bg.save('/public/favicon-dark.png')