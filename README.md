# BBradar update bot

## Installation
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
go install -v github.com/tomnomnom/anew@latest
```
## Running
```bash
cp .env.example .env
python main.py
```
## systemd
```bash
sudo cp bb-radar.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start bb-radar.service
sudo systemctl status bb-radar.service
sudo systemctl enable bb-radar.service
```
