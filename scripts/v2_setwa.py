import sqlite3
db = sqlite3.connect("/opt/pos/data/pos.db")
db.execute("INSERT OR REPLACE INTO config(clave,valor) VALUES('whatsapp','5491122334455')")
db.execute("INSERT OR REPLACE INTO config(clave,valor) VALUES('whatsapp_mensaje','Hola! Quiero hacer un pedido:')")
db.commit()
print("WA de prueba configurado")
