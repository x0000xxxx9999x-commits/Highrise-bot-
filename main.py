# -*- coding: utf-8 -*-
"""
بوت هايرايز متعدد المميزات
التشغيل:  highrise main:Bot ROOM_ID API_TOKEN
"""
import asyncio
import json
import os
import random
from datetime import datetime

from highrise import BaseBot, User, Position
from highrise.models import SessionMetadata, CurrencyItem, Item

# ====================== الإعدادات ======================
OWNERS = ["c1q"]          # أسماء الملاك في هايرايز (بالضبط كما تظهر)
WELCOME = "أهلاً وسهلاً {name} في غرفتنا 🌹 اكتب !help لعرض الأوامر"
BYE = "مع السلامة {name} 👋 نتمنى رجوعك"
ANNOUNCE_EVERY = 300                # إعلان تلقائي كل كم ثانية
ANNOUNCEMENTS = [
    "💡 اكتب !help لمعرفة أوامر البوت",
    "💃 اكتب رقم الرقصة (مثلاً 3) وستتكرر لك، واكتب stop للإيقاف",
    "🌹 لا تنسى تدعم الغرفة وتشارك أصدقاءك",
]
EMOTE_DELAY = 8                     # ثواني بين تكرار الرقصة
POS_FILE = "positions.json"

# ملاحظة: إن لم تعمل رقصة معينة غيّر معرّفها أو احذفها من القائمة
EMOTES = [
    "emote-hello", "emote-wave", "emote-bow", "emote-kiss", "emote-laughing",
    "emote-shy", "emote-sad", "emote-yes", "emote-no", "emote-thumbsup",
    "emote-clap", "emote-hug", "emote-snake", "emote-frog", "emote-superpose",
    "emote-zombierun", "emote-gordonshuffle", "emote-model", "emote-lust",
    "dance-tiktok2", "dance-blackpink", "dance-macarena", "dance-shoppingcart",
    "dance-russian", "dance-pennywise", "idle-dance-casual",
]
BALL = ["نعم 👍", "لا 👎", "ربما 🤔", "أكيد!", "مستحيل 😅", "اسأل لاحقاً"]
JOKES = [
    "مرة واحد غبي اشترى ساعة ذكية.. راحت تعلمه 😂",
    "قال لي صديقي: أنا ما أنام بدري.. قلت له: وأنا ما أصحى بدري 😴",
    "واحد سأل أبوه: ليش اسمي كذا؟ قال: لأنك ما خلّيتني أفكر 😆",
]
# ======================================================


def load_positions():
    if os.path.exists(POS_FILE):
        try:
            with open(POS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_positions(data):
    with open(POS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)


class Bot(BaseBot):
    def __init__(self):
        super().__init__()
        self.bot_id = None
        self.loops = {}                # user_id -> task
        self.positions = load_positions()

    # ---------------- أدوات مساعدة ----------------
    async def find_user(self, name):
        name = name.lstrip("@").lower()
        room = await self.highrise.get_room_users()
        for u, pos in room.content:
            if u.username.lower() == name:
                return u, pos
        return None, None

    async def is_mod(self, user: User):
        if user.username in OWNERS:
            return True
        try:
            perm = await self.highrise.get_room_privilege(user.id)
            return bool(perm.moderator or perm.designer)
        except Exception:
            return False

    def is_owner(self, user: User):
        return user.username in OWNERS

    async def emote_loop(self, user_id, emote):
        try:
            while True:
                await self.highrise.send_emote(emote, user_id)
                await asyncio.sleep(EMOTE_DELAY)
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    def stop_loop(self, user_id):
        task = self.loops.pop(user_id, None)
        if task:
            task.cancel()

    def start_loop(self, user_id, emote):
        self.stop_loop(user_id)
        self.loops[user_id] = asyncio.create_task(self.emote_loop(user_id, emote))

    async def announcer(self):
        i = 0
        while True:
            await asyncio.sleep(ANNOUNCE_EVERY)
            try:
                await self.highrise.chat(ANNOUNCEMENTS[i % len(ANNOUNCEMENTS)])
            except Exception:
                pass
            i += 1

    # ---------------- الأحداث ----------------
    async def on_start(self, session_metadata: SessionMetadata) -> None:
        self.bot_id = session_metadata.user_id
        print("البوت دخل الغرفة بنجاح ✅")
        if "home" in self.positions:
            p = self.positions["home"]
            try:
                await self.highrise.teleport(
                    self.bot_id, Position(p["x"], p["y"], p["z"], p.get("f", "FrontRight")))
            except Exception:
                pass
        await self.highrise.chat("البوت جاهز 🤖 اكتب !help")
        asyncio.create_task(self.announcer())
        self.start_loop(self.bot_id, "dance-tiktok2")   # البوت يرقص

    async def on_user_join(self, user: User, position) -> None:
        await self.highrise.chat(WELCOME.format(name=user.username))
        try:
            await self.highrise.send_emote("emote-wave", self.bot_id)
            await self.highrise.react("heart", user.id)
        except Exception:
            pass

    async def on_user_leave(self, user: User) -> None:
        self.stop_loop(user.id)
        await self.highrise.chat(BYE.format(name=user.username))

    async def on_tip(self, sender: User, receiver: User, tip) -> None:
        if receiver.id == self.bot_id and isinstance(tip, CurrencyItem):
            await self.highrise.chat(f"شكراً {sender.username} على الدعم 💛 ({tip.amount} جولد)")

    async def on_whisper(self, user: User, message: str) -> None:
        if message.strip().lower() in ("!help", "help", "مساعدة"):
            await self.send_help(user)

    async def send_help(self, user: User):
        lines = [
            "📜 الأوامر: !emotes | رقم | stop | !dice | !coin | !8ball | !joke | !time",
            "!love @اسم | !hug @اسم | !heart @اسم | !users | !tp اسم_المكان | !places",
        ]
        if await self.is_mod(user):
            lines.append("🛡️ المشرفين: !kick !ban !mute !unmute !bring !go !setpos !delpos !say")
        for line in lines:
            await self.highrise.send_whisper(user.id, line)

    # ---------------- الأوامر ----------------
    async def on_chat(self, user: User, message: str) -> None:
        msg = message.strip()
        if not msg:
            return

        # رقم = رقصة متكررة / stop = إيقاف
        if msg.isdigit():
            n = int(msg)
            if 1 <= n <= len(EMOTES):
                self.start_loop(user.id, EMOTES[n - 1])
            return
        if msg.lower() in ("stop", "0", "توقف"):
            self.stop_loop(user.id)
            return

        if not msg.startswith("!"):
            return
        parts = msg[1:].split()
        if not parts:
            return
        cmd, args = parts[0].lower(), parts[1:]

        # ---- عامة ----
        if cmd in ("help", "مساعدة", "اوامر"):
            await self.send_help(user)

        elif cmd in ("emotes", "رقصات"):
            chunk = [f"{i+1}:{e.split('-',1)[1]}" for i, e in enumerate(EMOTES)]
            for i in range(0, len(chunk), 8):
                await self.highrise.send_whisper(user.id, " | ".join(chunk[i:i+8]))

        elif cmd in ("dice", "نرد"):
            await self.highrise.chat(f"🎲 {user.username} حصل على {random.randint(1, 6)}")

        elif cmd in ("coin", "عملة"):
            await self.highrise.chat(f"🪙 {user.username}: {random.choice(['صورة', 'كتابة'])}")

        elif cmd in ("8ball", "سؤال"):
            await self.highrise.chat(f"🎱 {random.choice(BALL)}")

        elif cmd in ("joke", "نكتة"):
            await self.highrise.chat(random.choice(JOKES))

        elif cmd in ("time", "الوقت"):
            await self.highrise.chat("🕒 " + datetime.now().strftime("%Y-%m-%d %H:%M"))

        elif cmd in ("users", "عدد"):
            room = await self.highrise.get_room_users()
            await self.highrise.chat(f"👥 عدد الموجودين: {len(room.content)}")

        elif cmd in ("love", "حب") and args:
            await self.highrise.chat(
                f"💖 نسبة الحب بين {user.username} و {args[0].lstrip('@')}: {random.randint(10, 100)}%")

        elif cmd in ("hug", "حضن") and args:
            target, _ = await self.find_user(args[0])
            if target:
                await self.highrise.send_emote("emote-hug", user.id)
                await self.highrise.send_emote("emote-hug", target.id)

        elif cmd in ("heart", "قلب") and args:
            target, _ = await self.find_user(args[0])
            if target:
                await self.highrise.react("heart", target.id)

        elif cmd in ("places", "اماكن"):
            names = ", ".join(self.positions.keys()) or "لا يوجد أماكن محفوظة"
            await self.highrise.send_whisper(user.id, "📍 " + names)

        elif cmd in ("tp", "روح") and args:
            p = self.positions.get(args[0])
            if p:
                await self.highrise.teleport(
                    user.id, Position(p["x"], p["y"], p["z"], p.get("f", "FrontRight")))
            else:
                await self.highrise.send_whisper(user.id, "المكان غير موجود، اكتب !places")

        # ---- للمشرفين ----
        elif cmd in ("kick", "طرد", "ban", "حظر", "mute", "كتم", "unmute", "فك",
                     "bring", "جلب", "go", "اذهب", "setpos", "delpos", "say", "قل"):
            if not await self.is_mod(user):
                await self.highrise.send_whisper(user.id, "⛔ هذا الأمر للمشرفين فقط")
                return
            await self.mod_commands(user, cmd, args)

    async def mod_commands(self, user: User, cmd, args):
        if cmd in ("say", "قل"):
            await self.highrise.chat(" ".join(args))
            return

        if cmd in ("setpos", "delpos"):
            if not args:
                return
            if cmd == "delpos":
                self.positions.pop(args[0], None)
            else:
                room = await self.highrise.get_room_users()
                for u, pos in room.content:
                    if u.id == user.id and isinstance(pos, Position):
                        self.positions[args[0]] = {"x": pos.x, "y": pos.y, "z": pos.z,
                                                   "f": pos.facing}
            save_positions(self.positions)
            await self.highrise.send_whisper(user.id, "✅ تم")
            return

        if not args:
            return
        target, tpos = await self.find_user(args[0])
        if not target:
            await self.highrise.send_whisper(user.id, "لم أجد هذا المستخدم في الغرفة")
            return
        if target.username in OWNERS:
            return

        extra = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
        try:
            if cmd in ("kick", "طرد"):
                await self.highrise.moderate_room(target.id, "kick")
            elif cmd in ("ban", "حظر"):
                await self.highrise.moderate_room(target.id, "ban", extra or 3600)
            elif cmd in ("mute", "كتم"):
                await self.highrise.moderate_room(target.id, "mute", extra or 600)
            elif cmd in ("unmute", "فك"):
                await self.highrise.moderate_room(target.id, "mute", 1)
            elif cmd in ("bring", "جلب"):
                room = await self.highrise.get_room_users()
                for u, pos in room.content:
                    if u.id == user.id and isinstance(pos, Position):
                        await self.highrise.teleport(target.id, pos)
            elif cmd in ("go", "اذهب"):
                if isinstance(tpos, Position):
                    await self.highrise.teleport(user.id, tpos)
        except Exception as e:
            await self.highrise.send_whisper(user.id, f"خطأ: تأكد أن البوت مشرف في الغرفة ({e})")
