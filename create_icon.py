from PIL import Image, ImageDraw

def create_icon():
    size = (256, 256)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw a simple futuristic circle/eye
    center = (128, 128)
    radius = 120
    
    # Outer ring
    draw.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius], 
                 outline=(0, 255, 255), width=20)
    
    # Inner circle
    radius = 60
    draw.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius], 
                 fill=(0, 200, 255))
    
    # Center dot
    radius = 20
    draw.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius], 
                 fill=(255, 255, 255))

    img.save('assets/icon.ico', format='ICO')
    print("Icon created at assets/icon.ico")

if __name__ == "__main__":
    create_icon()
