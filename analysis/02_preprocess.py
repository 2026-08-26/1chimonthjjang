import pandas as pd


# =========================
# 1. 데이터 불러오기
# =========================

batter = pd.read_csv(
    "data/raw/KBO_batter_2019.csv"
)

player = pd.read_csv(
    "data/raw/KBO_player_info_full.csv"
)


# =========================
# 2. b'...' 형태 정리
# =========================

batter["gameinfo"] = (
    batter["gameinfo"]
    .astype(str)
    .str.replace("b'", "", regex=False)
    .str.replace("'", "", regex=False)
)

batter["team"] = (
    batter["team"]
    .astype(str)
    .str.replace("b'", "", regex=False)
    .str.replace("'", "", regex=False)
)


# =========================
# 3. 경기 날짜 만들기
# =========================

# gameinfo 앞 8자리 = YYYYMMDD
batter["game_date"] = pd.to_datetime(
    batter["gameinfo"].str[:8],
    format="%Y%m%d"
)


# =========================
# 4. 선수 정보 확인
# =========================

print("===== 선수 정보 컬럼 =====")
print(player.columns)

print("\n===== 선수 정보 앞부분 =====")
print(player.head())


# =========================
# 5. 현재 타자 데이터 확인
# =========================

print("\n===== 정리된 타자 데이터 =====")

print(
    batter[
        [
            "game_date",
            "gameinfo",
            "id",
            "team",
            "AB",
            "H",
            "R",
            "RBI"
        ]
    ].head(10)
)
# =========================
# 6. 선수 이름 붙이기
# =========================

# 선수 정보에서 필요한 컬럼만 가져오기
player_info = player[
    ["ID", "선수명", "season_2019"]
].copy()

# 컬럼 이름을 batter 쪽과 맞추기
player_info = player_info.rename(
    columns={
        "ID": "id",
        "선수명": "player_name",
        "season_2019": "team_2019"
    }
)

# 선수 ID 기준으로 합치기
batter = batter.merge(
    player_info,
    on="id",
    how="left"
)


# =========================
# 7. 결과 확인
# =========================

print("\n===== 선수 이름 연결 결과 =====")

print(
    batter[
        [
            "game_date",
            "player_name",
            "id",
            "team",
            "team_2019",
            "AB",
            "H",
            "R",
            "RBI"
        ]
    ].head(20)
)


print("\n선수 이름 없는 행:")
print(batter["player_name"].isna().sum())

print("\n전체 행:")
print(len(batter))

print("\n선수 수:")
print(batter["id"].nunique())

# =========================
# 8. 팀별 경기 데이터 불러오기
# =========================

team_game = pd.read_csv(
    "data/raw/edit_baseball_2019 (1).csv"
)

# 팀 경기 데이터의 날짜 형식 변환
team_game["game_date"] = pd.to_datetime(
    team_game["GDAY_DS"].astype(str),
    format="%Y%m%d"
)

print("\n===== 팀 경기 데이터 =====")
print(
    team_game[
        [
            "game_date",
            "T_ID",
            "VS_T_ID",
            "HIT",
            "HR",
            "RBI",
            "RUN",
            "OBP",
            "win"
        ]
    ].head(10)
)
# =========================
# 9. 선수 기록 + 팀 경기 기록 합치기
# =========================

# 필요한 팀 기록만 선택
team_for_merge = team_game[
    [
        "game_date",
        "T_ID",
        "VS_T_ID",
        "HIT",
        "HR",
        "RBI",
        "RUN",
        "OBP",
        "win"
    ]
].copy()

# 선수 기록과 이름이 겹치지 않도록 변경
team_for_merge = team_for_merge.rename(
    columns={
        "T_ID": "team",
        "VS_T_ID": "opponent",
        "HIT": "team_H",
        "HR": "team_HR",
        "RBI": "team_RBI",
        "RUN": "team_RUN",
        "OBP": "team_OBP",
        "win": "team_win"
    }
)

# =========================
# 더블헤더 경기 제외
# 2019-09-19 OB-SK는 1, 2차전 구분 문제로 분석에서 제외
# =========================

batter = batter[
    ~(
        (batter["game_date"] == pd.Timestamp("2019-09-19")) &
        (batter["team"].isin(["OB", "SK"]))
    )
].copy()

team_for_merge = team_for_merge[
    ~(
        (team_for_merge["game_date"] == pd.Timestamp("2019-09-19")) &
        (team_for_merge["team"].isin(["OB", "SK"]))
    )
].copy()


# 선수 + 팀 데이터 연결
merged = batter.merge(
    team_for_merge,
    on=["game_date", "team"],
    how="left"
)
# 날짜 + 소속팀을 기준으로 연결
merged = batter.merge(
    team_for_merge,
    on=["game_date", "team"],
    how="left"
)
# =========================
# 10. 병합 결과 확인
# =========================

print("\n===== 선수 + 팀 데이터 =====")

print(
    merged[
        [
            "game_date",
            "player_name",
            "team",
            "opponent",
            "AB",
            "H",
            "RBI",
            "team_H",
            "team_HR",
            "team_RUN",
            "team_OBP",
            "team_win"
        ]
    ].head(30)
)


print("\n===== 팀 데이터 연결 상태 =====")

print("전체 선수 기록:", len(merged))

print(
    "팀 경기 정보가 없는 기록:",
    merged["opponent"].isna().sum()
)

print(
    "팀 경기 정보가 연결된 기록:",
    merged["opponent"].notna().sum()
)
# =========================
# 11. 팀 데이터 중복 확인
# =========================

duplicate_team = team_game[
    team_game.duplicated(
        subset=["game_date", "T_ID"],
        keep=False
    )
].sort_values(
    ["game_date", "T_ID"]
)

print("\n===== 같은 날짜 + 같은 팀이 여러 개인 경기 =====")

print(
    duplicate_team[
        [
            "game_date",
            "T_ID",
            "VS_T_ID",
            "RUN",
            "HIT",
            "HR",
            "win"
        ]
    ]
)

print("\n중복 행 개수:", len(duplicate_team))


# 선수 데이터에서도 해당 날짜 확인
print("\n===== 선수 gameinfo 중복 경기 확인 =====")

duplicate_keys = duplicate_team[
    ["game_date", "T_ID"]
].drop_duplicates()

check_players = batter.merge(
    duplicate_keys,
    left_on=["game_date", "team"],
    right_on=["game_date", "T_ID"],
    how="inner"
)

print(
    check_players[
        [
            "game_date",
            "gameinfo",
            "player_name",
            "team"
        ]
    ].head(100)
)
# =========================
# 12. 연결 실패 날짜 확인
# =========================

not_matched = merged[
    merged["opponent"].isna()
].copy()

print("\n===== 팀 데이터 연결 실패 기간 =====")

print("최초 날짜:", not_matched["game_date"].min())
print("마지막 날짜:", not_matched["game_date"].max())

print("\n날짜별 연결 실패 수:")
print(
    not_matched["game_date"]
    .value_counts()
    .sort_index()
)

# =========================
# 전처리 완료 데이터 저장
# =========================
# 팀 데이터가 없는 3월 23일 ~ 31일 선수 기록 제거
merged = merged.dropna(subset=["opponent"]).copy()

print("\n===== 전처리 최종 결과 =====")
print("최종 데이터 크기:", merged.shape)
print("선수 수:", merged["id"].nunique())
print("팀 정보 없는 행:", merged["opponent"].isna().sum())
print("시작 날짜:", merged["game_date"].min())
print("마지막 날짜:", merged["game_date"].max())

merged.to_csv(
    "data/processed/baseball_2019_merged.csv",
    index=False,
    encoding="utf-8-sig"
)
merged.to_csv(
    "data/processed/baseball_2019_merged.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\n===== 전처리 최종 결과 =====")
print("최종 데이터 크기:", merged.shape)
print("선수 수:", merged["id"].nunique())
print("팀 정보 없는 행:", merged["opponent"].isna().sum())
print("시작 날짜:", merged["game_date"].min())
print("마지막 날짜:", merged["game_date"].max())

print("\n저장 완료!")
print("data/processed/baseball_2019_merged.csv")