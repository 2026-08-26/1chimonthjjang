import pandas as pd

# encoding 옵션을 utf-8-sig 로 변경
df_naver = pd.read_csv('data/raw/naver.csv', encoding='utf-8-sig')
df_kdrama = pd.read_csv('data/raw/kdrama.csv', encoding='utf-8-sig')
df_kpop = pd.read_csv('data/raw/kpopidolsv3.csv', encoding='utf-8-sig')

print("=== Naver 데이터 ===")
print(df_naver.head())

print("\n=== K-Drama 데이터 ===")
print(df_kdrama.head())

print("\n=== K-Pop 데이터 ===")
print(df_kpop.head())