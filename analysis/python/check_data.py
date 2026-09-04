import pandas as pd

apart = pd.read_csv(
    "data/raw/Apart Deal.csv",
    low_memory=False
)

print("=== 아파트 데이터 ===")

print("\n데이터 크기")
print(apart.shape)

print("\n컬럼명")
print(apart.columns.tolist())

print("\n앞 5행")
print(apart.head())

print("\n데이터 타입")
print(apart.dtypes)

rate = pd.read_csv(
    "data/raw/base_rate.csv",
    low_memory=False
)

print("\n=== 금리 데이터 ===")

print("\n데이터 크기")
print(rate.shape)

print("\n컬럼명")
print(rate.columns.tolist())

print("\n앞 5행")
print(rate.head())

print("\n데이터 타입")
print(rate.dtypes)

population = pd.read_csv(
    "data/raw/Korean_demographics.csv",
    low_memory=False
)

print("\n=== 인구 데이터 ===")

print("\n데이터 크기")
print(population.shape)

print("\n컬럼명")
print(population.columns.tolist())

print("\n앞 5행")
print(population.head())

print("\n데이터 타입")
print(population.dtypes)

migration = pd.read_csv(
    "data/raw/population_migration.csv",
    low_memory=False
)

print("\n=== 인구이동 데이터 ===")

print("\n데이터 크기")
print(migration.shape)

print("\n컬럼명")
print(migration.columns.tolist())

print("\n앞 5행")
print(migration.head())

print("\n데이터 타입")
print(migration.dtypes)