# CMIT Shift Report Control

Ung dung Streamlit ho tro tao bao cao san luong tung ca CMIT, import log N4/MoveEvent, luu lich su ca bang SQLite, nhap tay cac chi so Gate/CHE/Vessel Notes va xuat Shift Operation Report dang Excel.

## Ban code chinh thuc

File chay chinh cua du an:

```text
app.py
```

Source chinh nam o `app.py` va package `cmit/`. Cac ban thu nghiem cu da duoc gom vao `archive/legacy/` de tham khao khi can.

## Link deploy

Ung dung dang chay tren Streamlit Community Cloud:

```text
https://cmit-berth-planner-demo-01.streamlit.app/
```

## Chay tren local

Khi chay local bang Streamlit, ung dung mac dinh mo tai:

```text
http://localhost:8501
```

Neu may tinh co hien Network URL, co the truy cap tu may khac cung mang LAN bang dia chi dang:

```text
http://<IP-may-cua-ban>:8501
```

## Cach khoi dong du an

Lenh nhanh de mo du an:

```powershell
cd E:\Learn\Python\AI
.\project.cmd start
```

Lenh nay se tu dong:

- Tao `.venv` neu chua co.
- Cai dat thu vien trong `requirements.txt` neu can.
- Chay Streamlit tren `http://localhost:8501`.
- Mo trinh duyet.
- Mo folder du an trong VSCode neu may co lenh `code`.

Lenh nhanh de tat du an:

```powershell
cd E:\Learn\Python\AI
.\project.cmd stop
```

Khoi dong lai du an:

```powershell
cd E:\Learn\Python\AI
.\project.cmd restart
```

Kiem tra du an dang chay hay chua:

```powershell
cd E:\Learn\Python\AI
.\project.cmd status
```

Neu khong muon go lenh, co the double-click:

```text
START_PROJECT.cmd
STOP_PROJECT.cmd
```

### Cach chay thu cong

Mo PowerShell hoac Terminal trong thu muc du an:

```powershell
cd E:\Learn\Python\AI
```

Tao moi truong ao Python:

```powershell
python -m venv .venv
```

Kich hoat moi truong ao:

```powershell
.\.venv\Scripts\Activate.ps1
```

Cai dat thu vien:

```powershell
pip install -r requirements.txt
```

Chay ung dung:

```powershell
streamlit run app.py
```

Sau khi chay, mo trinh duyet tai:

```text
http://localhost:8501
```

## Chuc nang chinh

- Tao hoac mo lai ca lam viec theo quy tac CMIT:
  - `D1`: 06:00 den truoc 18:00.
  - `D2`: 18:00 den truoc 06:00 ngay hom sau.
- Upload file N4/MoveEvent hoac workbook co sheet `DATA`.
- Review va chinh classification theo carrier: `VESSEL`, `BARGE`, `GATE`, `YARD`.
- Nhap tay thong tin personnel, Gate email, HK Moves, CHE availability, delay 5x, vessel notes va equipment breakdown.
- Xuat file:

```text
SHIFT_REPORT_YYYY-MM-DD_D1.xlsx
SHIFT_REPORT_YYYY-MM-DD_D2.xlsx
```

App dong thoi sinh noi dung email draft de kiem tra va gui thu cong.

## Template bao cao

File template Excel dang nam tai:

```text
docs/SHIFT_REPORT_2026-05-28_D2.xlsx
```

Danh sach delay code tham khao nam tai:

```text
docs/Delay sheet- (updated 25 May 2026).xlsx
```

Template duoc dung de giu format cho cac sheet `SUMMARY REPORT`, `CRANE STATS`, `VESSEL REPORT`, `BARGE REPORT`, `VESSEL NOTES`, `EQUIPMENT BREAKDOWN`, `DATA`.

## Cau truc du an

```text
E:\Learn\Python\AI
|-- app.py
|-- cmit/
|-- tests/
|-- docs/
|-- sample_data/
|-- archive/
|-- requirements.txt
|-- packages.txt
|-- project.ps1
|-- project.cmd
|-- START_PROJECT.cmd
`-- STOP_PROJECT.cmd
```

Trong do:

- `app.py`: file Streamlit chinh cua du an.
- `cmit/`: backend nghiep vu gom import N4, tinh KPI, SQLite storage, export Excel va email draft.
- `tests/`: unit tests cho shift rules, importer, KPI va export workbook.
- `docs/`: template bao cao Excel va Delay Sheet goc.
- `sample_data/`: file du lieu mau dung de test nhanh, gom `MoveEvent_20260526_2203.xlsx` va `Book1.csv`.
- `archive/legacy/`: code thu nghiem cu tu `Demo/` va `Demo 2/` da doi ten ro rang.
- `requirements.txt`: danh sach thu vien Python can cai.
- `packages.txt`: file cau hinh package he thong cho Streamlit Cloud, hien dang de trong.
- `project.ps1`: script mo/tat/restart/kiem tra du an tren local.
- `project.cmd`: lenh wrapper de chay `project.ps1` ma khong bi chan boi PowerShell Execution Policy.
- `START_PROJECT.cmd`: file double-click de mo du an.
- `STOP_PROJECT.cmd`: file double-click de tat du an.

Thu muc runtime khong commit:

- `data/`: SQLite database va source files da upload.
- `outputs/`: cac file report Excel sinh ra.

## Kiem thu

Chay unit tests:

```powershell
cd E:\Learn\Python\AI
.\.venv\Scripts\python.exe -m unittest discover -v
```

## Xu ly loi thuong gap

Neu PowerShell khong cho kich hoat `.venv`, chay lenh sau roi kich hoat lai:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Neu cong `8501` dang bi dung, chay bang cong khac:

```powershell
streamlit run app.py --server.port 8502
```

Sau do mo:

```text
http://localhost:8502
```

## Cap nhat code len GitHub

Kiem tra thay doi:

```powershell
git status
```

Them file can commit:

```powershell
git add app.py requirements.txt README.md
```

Commit:

```powershell
git commit -m "Update project documentation"
```

Push len GitHub:

```powershell
git push origin main
```
