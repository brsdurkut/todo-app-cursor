def faktoriyel_hesapla(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * faktoriyel_hesapla(n - 1)

def main():
    try:
        sayi = int(input("Lütfen faktöriyelini hesaplamak istediğiniz sayıyı girin: "))
        
        if sayi < 0:
            print("Lütfen pozitif bir sayı girin!")
        else:
            sonuc = faktoriyel_hesapla(sayi)
            print(f"{sayi}! = {sonuc}")
            
    except ValueError:
        print("Lütfen geçerli bir sayı girin!")

if __name__ == "__main__":
    main()
