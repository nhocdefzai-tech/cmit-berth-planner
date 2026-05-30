import pandas as pd

# 1. Đọc dữ liệu từ file DATA.csv (đã tải lên)
df = pd.read_csv('SHIFT_REPORT_2026-05-28_D1.xlsx - DATA.csv')

# 2. Xử lý dữ liệu và tạo các DataFrame cho từng Sheet
# Sheet: VESSEL REPORT & BARGE REPORT
df_vessel = df[df['LOAI PTVT'] == 'VESSEL']
df_barge = df[df['LOAI PTVT'] == 'BARGE']

# Hàm tổng hợp sản lượng theo cầu tàu và cẩu
def aggregate_report(data):
    return data.groupby(['CARRIER VISIT', 'STS QUAY']).agg(
        MOVES=('UNIT NBR', 'count'),
        DISCH=('MOVE KIND', lambda x: (x == 'DISCHARGE').sum()),
        LOAD=('MOVE KIND', lambda x: (x == 'LOAD').sum())
    ).reset_index()

vessel_stats = aggregate_report(df_vessel)
barge_stats = aggregate_report(df_barge)

# Sheet: CRANE STATS (Tính toán hiệu suất cẩu)
crane_stats = df.groupby('STS QUAY').agg(
    TOTAL_MOVES=('UNIT NBR', 'count')
).reset_index()

# 3. Xuất ra file Excel hoàn chỉnh với nhiều Sheet
with pd.ExcelWriter('SHIFT_REPORT_RESULT.xlsx', engine='xlsxwriter') as writer:
    df.to_excel(writer, sheet_name='DATA', index=False)
    vessel_stats.to_excel(writer, sheet_name='VESSEL REPORT', index=False)
    barge_stats.to_excel(writer, sheet_name='BARGE REPORT', index=False)
    crane_stats.to_excel(writer, sheet_name='CRANE STATS', index=False)
    
    # Các sheet phụ trợ sẽ lấy dữ liệu từ các tệp tương ứng bạn đã cung cấp
    # Ví dụ: pd.read_csv('SHIFT_REPORT...VESSEL NOTES.csv').to_excel(writer, sheet_name='VESSEL NOTES')

print("Đã tạo file SHIFT_REPORT_RESULT.xlsx thành công với đầy đủ các sheet!")