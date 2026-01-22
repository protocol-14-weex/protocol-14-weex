# 🚀 Deployment Instructions (Digital Ocean VPS)

## 1. Prepare Files
Run the bundle script locally to create a zip file:
```bash
python make_bundle.py
```
This will create a file like `weex_bot_vps_20260121_xxxx.zip`.

## 2. Upload to VPS
Use `scp` to upload the zip file to your VPS:
```bash
scp weex_bot_vps_*.zip root@178.128.65.112:/root/
```

## 3. Connect to VPS
```bash
ssh root@178.128.65.112
```

## 4. Setup on VPS
Once logged in:

```bash
# Install unzip if needed
apt-get update && apt-get install -y unzip python3-pip

# Unzip
unzip weex_bot_vps_*.zip -d weex_bot
cd weex_bot

# Create .env file (CRITICAL!)
nano .env
```
Paste your API credentials into `.env`:
```env
WEEX_API_KEY=your_key
WEEX_SECRET_KEY=your_secret
WEEX_PASSPHRASE=your_passphrase
COINGECKO_API_KEY=your_coingecko_key (optional)
```
Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`).

## 5. Run with Docker (Recommended)
If you have Docker installed:
```bash
docker build -t weex-bot .
docker run -d --name weex-bot --restart unless-stopped --env-file .env weex-bot
```

## 6. Run Manually (Alternative)
```bash
pip3 install -r requirements.txt
python3 conservative_grid.py
```

## 7. Useful Commands
```bash
# Check logs
docker logs -f weex-bot

# Stop bot
docker stop weex-bot

# Restart bot
docker restart weex-bot
```
