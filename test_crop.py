import requests

# 1. Provide an image (just pick one locally)
with open("test_image.jpg", "wb") as f:
    f.write(b"fake image data")

with open("test_image.jpg", "rb") as f:
    files = {"file": ("cropped_image.png", f, "image/png")}
    response = requests.post("http://localhost:8000/search", files=files, data={"page": 1})

print(response.status_code)
print(response.text)
