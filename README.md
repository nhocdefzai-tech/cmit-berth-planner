# CMIT Berth Planner & Performance Dashboard

Ung dung Streamlit ho tro quan ly cau ben CMIT, lap so do phan luong sa lan, theo doi nang suat khai thac va quan ly cac ma giam tru delay 5x.

## Ban code chinh thuc

File chay chinh cua du an:

```text
app.py
```

Cac thu muc `Demo/` va `Demo 2/` hien la ban thu nghiem/ban cu, khong dung lam source chinh de phat trien tiep.

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

## Du lieu dau vao

Ung dung hien dang doc file log N4:

```text
MoveEvent_20260526_2203.xlsx
```

File nay can nam cung thu muc voi `app.py`.

## Cau truc du an

```text
E:\Learn\Python\AI
|-- app.py
|-- MoveEvent_20260526_2203.xlsx
|-- requirements.txt
|-- packages.txt
|-- project.ps1
|-- project.cmd
|-- START_PROJECT.cmd
|-- STOP_PROJECT.cmd
|-- Demo/
`-- Demo 2/
```

Trong do:

- `app.py`: file Streamlit chinh cua du an.
- `MoveEvent_20260526_2203.xlsx`: file du lieu log N4 dang duoc app doc.
- `requirements.txt`: danh sach thu vien Python can cai.
- `packages.txt`: file cau hinh package he thong cho Streamlit Cloud, hien dang de trong.
- `project.ps1`: script mo/tat/restart/kiem tra du an tren local.
- `project.cmd`: lenh wrapper de chay `project.ps1` ma khong bi chan boi PowerShell Execution Policy.
- `START_PROJECT.cmd`: file double-click de mo du an.
- `STOP_PROJECT.cmd`: file double-click de tat du an.
- `Demo/`: ban demo cu.
- `Demo 2/`: ung dung/phien ban thu nghiem khac.

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
