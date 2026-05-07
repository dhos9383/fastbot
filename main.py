from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioPiped
import asyncio

# --- ضع معلوماتك هنا ---
api_id = 23392039         # ضع الآيدي الخاص بك
api_hash = "e5027f6a4b2d4103300ff23b2c265789"    # ضع الهاش الخاص بك
# ---------------------

app = Client("1ApWapzMBuwf_9KbsPMDn4z6nUuMKMeuFeZ5Z2WTkLuE5B1WkgmVp9gzQutp0dVDqB4ljD8qtkhAVBplLq0Jhz2LXCn-sytRZsPMbLplQAAVSnkOWkVQibZ42NsYtDmeW-LAv2yxJZPgdUcuRcWeuhqVZeHhPnBvZeGRHHTHFK81yIKOCdIaaT_f3P5V8pJ_eMdiixJ02C9JG_wSOe7gmLMQLu_2gv38FxpFkakDQLD8PAifVE8UwsZWF2i_B9GmZxfF4-MW_gOd1vOdeil5Vp7HvyINj9wN34eFa3C6rB0-4HzWSHPUh7wJJEtPbitJRBNnQaV-HD18u0Uz5KwzQLzt0oFp9uLw=", api_id=api_id, api_hash=api_hash)
call_py = PyTgCalls(app)

async def main():
    await app.start()
    print("✅ السكربت بدأ العمل!")
    print("الآن اكتب رقمك في الأسفل إذا طلب منك ذلك..")
    await call_py.start()
    
    # يبقى السكربت يعمل في الخلفية
    await asyncio.Event().wait()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
