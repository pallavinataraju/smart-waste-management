import qrcode

url = "http://192.168.31.212:8000/bin/bin001/"

qr = qrcode.make(url)

qr.save("BIN001_QR.png")

print("BIN001 QR code created successfully!")