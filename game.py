import random
n = random.randint(1, 10)
print("Adivina el número (1-10)")
for i in range(3):
    g = int(input(f"Intento {i+1}/3: "))
    if g == n: print("🎉 Ganaste!"); break
    print("Alto" if g > n else "Bajo")
else:
    print(f"Perdiste! Era el {n}")
