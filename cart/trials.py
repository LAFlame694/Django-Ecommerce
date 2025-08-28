import smtplib

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
print("TLS handshake succeeded")
server.quit()
