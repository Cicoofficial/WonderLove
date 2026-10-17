import os, re, secrets
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Add your Neon connection string in Render Environment.")
UPLOAD_FOLDER = os.path.join(APP_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-before-launch-" + secrets.token_hex(16))
app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

LANGUAGES = {
    "en": "English", "fr": "Français", "es": "Español", "pt": "Português",
    "ar": "العربية", "de": "Deutsch", "zh": "中文", "sw": "Kiswahili",
    "yo": "Yorùbá", "ha": "Hausa", "ig": "Igbo"
}
UI = {
"en": {"home":"Where Hearts Meet and Beautiful Stories Begin.","join":"Create Free Account","login":"Log In","logout":"Log Out","discover":"Discover people","matches":"Matches","messages":"Messages","profile":"My profile","welcome":"Find your special someone.","intro":"Meet people, build connections, and discover meaningful relationships.","name":"Display name","email":"Email address","password":"Password","confirm":"Confirm password","dob":"Date of birth","sex":"Sex","male":"Male","female":"Female","country":"Country","bio":"About me","interests":"Interests","intentions":"Relationship intentions","looking":"Interested in","save":"Save","register":"Register","already":"Already have an account?","need":"New to WonderLove?","send":"Send message","like":"Like","edit":"Edit profile","no_people":"No profiles found yet. Check back soon!","limited":"You have used your introductory messages for now. Match with this person to continue chatting.","message":"Message","language":"Language","search":"Search","age_from":"Age from","age_to":"Age to","any_country":"Any country","report":"Report","block":"Block","delete":"Delete account","original":"Original message","translate":"Translate","about":"A welcoming place to meet people worldwide.","privacy":"Privacy","terms":"Terms","contact":"Contact","passwords":"Passwords must match.","age_error":"You must be 18 or older to join.","intro_limit":"You have reached your introductory-message limit. Like each other to match and continue chatting.","unread":"Unread"},
"fr": {"home":"Là où les cœurs se rencontrent et où naissent de belles histoires.","join":"Créer un compte gratuit","login":"Se connecter","logout":"Se déconnecter","discover":"Découvrir","matches":"Correspondances","messages":"Messages","profile":"Mon profil","welcome":"Trouvez la personne qui vous correspond.","intro":"Rencontrez des personnes et créez des liens sincères.","name":"Nom affiché","email":"Adresse e-mail","password":"Mot de passe","confirm":"Confirmer le mot de passe","dob":"Date de naissance","sex":"Sexe","male":"Homme","female":"Femme","country":"Pays","bio":"À propos de moi","interests":"Centres d’intérêt","intentions":"Intentions relationnelles","looking":"Je recherche","save":"Enregistrer","register":"S’inscrire","already":"Vous avez déjà un compte ?","need":"Nouveau sur WonderLove ?","send":"Envoyer un message","like":"J’aime","edit":"Modifier le profil","no_people":"Aucun profil pour le moment.","message":"Message","language":"Langue","search":"Rechercher","age_from":"Âge minimum","age_to":"Âge maximum","any_country":"Tous les pays","report":"Signaler","block":"Bloquer","delete":"Supprimer le compte","translate":"Traduire"},
"es": {"home":"Donde se encuentran los corazones y nacen historias bonitas.","join":"Crear cuenta gratis","login":"Iniciar sesión","logout":"Cerrar sesión","discover":"Descubrir personas","matches":"Conexiones","messages":"Mensajes","profile":"Mi perfil","welcome":"Encuentra a alguien especial.","intro":"Conoce personas y crea conexiones significativas.","name":"Nombre visible","email":"Correo electrónico","password":"Contraseña","confirm":"Confirmar contraseña","dob":"Fecha de nacimiento","sex":"Sexo","male":"Hombre","female":"Mujer","country":"País","bio":"Sobre mí","interests":"Intereses","intentions":"Intenciones de relación","looking":"Me interesa","save":"Guardar","register":"Registrarse","already":"¿Ya tienes una cuenta?","need":"¿Nuevo en WonderLove?","send":"Enviar mensaje","like":"Me gusta","edit":"Editar perfil","no_people":"Todavía no hay perfiles.","message":"Mensaje","language":"Idioma","search":"Buscar","age_from":"Edad mínima","age_to":"Edad máxima","any_country":"Todos los países","report":"Denunciar","block":"Bloquear","delete":"Eliminar cuenta","translate":"Traducir"},
"pt": {"home":"Onde corações se encontram e belas histórias começam.","join":"Criar conta grátis","login":"Entrar","logout":"Sair","discover":"Descobrir pessoas","matches":"Combinações","messages":"Mensagens","profile":"Meu perfil","welcome":"Encontre alguém especial.","intro":"Conheça pessoas e crie conexões significativas.","name":"Nome de exibição","email":"E-mail","password":"Senha","confirm":"Confirmar senha","dob":"Data de nascimento","sex":"Sexo","male":"Homem","female":"Mulher","country":"País","bio":"Sobre mim","interests":"Interesses","intentions":"Intenção de relacionamento","looking":"Tenho interesse em","save":"Salvar","register":"Cadastrar","already":"Já tem uma conta?","need":"Novo no WonderLove?","send":"Enviar mensagem","like":"Curtir","edit":"Editar perfil","no_people":"Ainda não há perfis.","message":"Mensagem","language":"Idioma","search":"Pesquisar","age_from":"Idade mínima","age_to":"Idade máxima","any_country":"Todos os países","report":"Denunciar","block":"Bloquear","delete":"Excluir conta","translate":"Traduzir"},
"de": {"home":"Wo Herzen sich begegnen und schöne Geschichten beginnen.","join":"Kostenlos registrieren","login":"Anmelden","logout":"Abmelden","discover":"Menschen entdecken","matches":"Matches","messages":"Nachrichten","profile":"Mein Profil","welcome":"Finde einen besonderen Menschen.","intro":"Lerne Menschen kennen und knüpfe echte Verbindungen.","name":"Anzeigename","email":"E-Mail-Adresse","password":"Passwort","confirm":"Passwort bestätigen","dob":"Geburtsdatum","sex":"Geschlecht","male":"Männlich","female":"Weiblich","country":"Land","bio":"Über mich","interests":"Interessen","intentions":"Beziehungsabsichten","looking":"Ich suche","save":"Speichern","register":"Registrieren","already":"Schon ein Konto?","need":"Neu bei WonderLove?","send":"Nachricht senden","like":"Gefällt mir","edit":"Profil bearbeiten","no_people":"Noch keine Profile vorhanden.","message":"Nachricht","language":"Sprache","search":"Suchen","age_from":"Mindestalter","age_to":"Höchstalter","any_country":"Alle Länder","report":"Melden","block":"Blockieren","delete":"Konto löschen","translate":"Übersetzen"},
"sw": {"home":"Mahali mioyo hukutana na hadithi nzuri huanza.","join":"Fungua akaunti bila malipo","login":"Ingia","logout":"Toka","discover":"Gundua watu","matches":"Mechi","messages":"Ujumbe","profile":"Wasifu wangu","welcome":"Mpate mtu wa pekee.","intro":"Kutana na watu na kujenga mahusiano yenye maana.","name":"Jina la kuonyesha","email":"Barua pepe","password":"Nenosiri","confirm":"Thibitisha nenosiri","dob":"Tarehe ya kuzaliwa","sex":"Jinsia","male":"Mwanaume","female":"Mwanamke","country":"Nchi","bio":"Kuhusu mimi","interests":"Mapendeleo","intentions":"Nia ya uhusiano","looking":"Ninavutiwa na","save":"Hifadhi","register":"Jisajili","already":"Una akaunti tayari?","need":"Mgeni WonderLove?","send":"Tuma ujumbe","like":"Penda","edit":"Hariri wasifu","no_people":"Hakuna wasifu bado.","message":"Ujumbe","language":"Lugha","search":"Tafuta","age_from":"Umri wa chini","age_to":"Umri wa juu","any_country":"Nchi yoyote","report":"Ripoti","block":"Zuia","delete":"Futa akaunti","translate":"Tafsiri"},
"ar": {"home":"حيث تلتقي القلوب وتبدأ القصص الجميلة.","join":"إنشاء حساب مجاني","login":"تسجيل الدخول","logout":"تسجيل الخروج","discover":"اكتشف أشخاصًا","matches":"التطابقات","messages":"الرسائل","profile":"ملفي الشخصي","welcome":"اعثر على شخص مميز.","intro":"تعرّف على أشخاص وابنِ علاقات ذات معنى.","name":"اسم العرض","email":"البريد الإلكتروني","password":"كلمة المرور","confirm":"تأكيد كلمة المرور","dob":"تاريخ الميلاد","sex":"الجنس","male":"ذكر","female":"أنثى","country":"البلد","bio":"نبذة عني","interests":"الاهتمامات","intentions":"نية العلاقة","looking":"أبحث عن","save":"حفظ","register":"إنشاء حساب","already":"لديك حساب بالفعل؟","need":"جديد في WonderLove؟","send":"إرسال رسالة","like":"إعجاب","edit":"تعديل الملف الشخصي","no_people":"لا توجد ملفات شخصية بعد.","message":"رسالة","language":"اللغة","search":"بحث","age_from":"أقل عمر","age_to":"أعلى عمر","any_country":"أي بلد","report":"إبلاغ","block":"حظر","delete":"حذف الحساب","translate":"ترجمة"},
"zh": {"home":"让心相遇，让美好故事开始。","join":"免费创建账户","login":"登录","logout":"退出","discover":"发现新朋友","matches":"配对","messages":"消息","profile":"我的资料","welcome":"寻找特别的那个人。","intro":"认识新朋友，建立有意义的联系。","name":"显示名称","email":"电子邮箱","password":"密码","confirm":"确认密码","dob":"出生日期","sex":"性别","male":"男","female":"女","country":"国家","bio":"关于我","interests":"兴趣","intentions":"关系意向","looking":"我感兴趣的人","save":"保存","register":"注册","already":"已有账户？","need":"初次使用 WonderLove？","send":"发送消息","like":"喜欢","edit":"编辑资料","no_people":"暂时没有个人资料。","message":"消息","language":"语言","search":"搜索","age_from":"最低年龄","age_to":"最高年龄","any_country":"任何国家","report":"举报","block":"屏蔽","delete":"删除账户","translate":"翻译"},
"yo": {"home":"Ibi tí ọkàn ti pàdé, tí ìtàn ẹlẹ́wà sì ti bẹ̀rẹ̀.","join":"Ṣẹ̀dá àkọọ́lẹ̀ lọ́fẹ̀ẹ́","login":"Wọlé","logout":"Jáde","discover":"Ṣàwárí àwọn ènìyàn","matches":"Àwọn tó bá ara mu","messages":"Àwọn ìfiránṣẹ́","profile":"Profaili mi","welcome":"Wá ẹni pàtàkì rẹ.","intro":"Pàdé àwọn ènìyàn kí o sì dá ìbáṣepọ̀ tó ní ìtumọ̀ sílẹ̀.","name":"Orúkọ ìfihàn","email":"Àdírẹ́sì ímeèlì","password":"Ọ̀rọ̀ aṣínà","confirm":"Jẹ́rìí ọ̀rọ̀ aṣínà","dob":"Ọjọ́ ìbí","sex":"Ìbálòpọ̀","male":"Ọkùnrin","female":"Obìnrin","country":"Orílẹ̀-èdè","bio":"Nípa mi","interests":"Ohun tí mo fẹ́ràn","intentions":"Ète ìbáṣepọ̀","looking":"Mo fẹ́ pàdé","save":"Fipamọ́","register":"Forúkọ sílẹ̀","already":"Ṣé o ti ní àkọọ́lẹ̀?","need":"Ṣé o ṣẹ̀ṣẹ̀ dé WonderLove?","send":"Fi ìfiránṣẹ́ ránṣẹ́","like":"Fẹ́ràn","edit":"Ṣàtúnṣe profaili","no_people":"Kò sí profaili lọ́wọ́lọ́wọ́.","message":"Ìfiránṣẹ́","language":"Èdè","search":"Ṣàwárí","age_from":"Ọjọ́ orí tó kéré jù","age_to":"Ọjọ́ orí tó pọ̀ jù","any_country":"Orílẹ̀-èdè èyíkéyìí","report":"Jábọ̀","block":"Dí lọ́wọ́","delete":"Pa àkọọ́lẹ̀ rẹ́","translate":"Túmọ̀"},
"ha": {"home":"Inda zukata ke haɗuwa, kyawawan labarai su fara.","join":"Ƙirƙiri asusu kyauta","login":"Shiga","logout":"Fita","discover":"Gano mutane","matches":"Daidaito","messages":"Saƙonni","profile":"Bayanan martaba na","welcome":"Nemo mutum na musamman.","intro":"Haɗu da mutane kuma ku gina kyakkyawar alaƙa.","name":"Sunan nuni","email":"Adireshin imel","password":"Kalmar sirri","confirm":"Tabbatar da kalmar sirri","dob":"Ranar haihuwa","sex":"Jinsi","male":"Namiji","female":"Mace","country":"Ƙasa","bio":"Game da ni","interests":"Abubuwan sha'awa","intentions":"Manufar dangantaka","looking":"Ina sha'awar","save":"Ajiye","register":"Yi rajista","already":"Kana da asusu?","need":"Sabon mai amfani da WonderLove?","send":"Aika saƙo","like":"So","edit":"Gyara bayanai","no_people":"Babu bayanan martaba tukuna.","message":"Saƙo","language":"Harshe","search":"Nema","age_from":"Mafi ƙarancin shekaru","age_to":"Mafi yawan shekaru","any_country":"Duk ƙasashe","report":"Kai rahoto","block":"Toshe","delete":"Goge asusu","translate":"Fassara"},
"ig": {"home":"Ebe obi na-ezukọ ma akụkọ mara mma amalite.","join":"Mepụta akaụntụ n'efu","login":"Banye","logout":"Pụọ","discover":"Chọpụta ndị mmadụ","matches":"Ndị kwekọrọ","messages":"Ozi","profile":"Profaịlụ m","welcome":"Chọta onye pụrụ iche gị.","intro":"Zute ndị mmadụ ma wuo mmekọrịta bara uru.","name":"Aha ngosi","email":"Adreesị ozi-e","password":"Okwuntughe","confirm":"Kwenye okwuntughe","dob":"Ụbọchị ọmụmụ","sex":"Esemokwu nwoke/nwanyị","male":"Nwoke","female":"Nwanyị","country":"Obodo","bio":"Maka m","interests":"Ihe ndị masịrị m","intentions":"Ebumnuche mmekọrịta","looking":"Mmasị m bụ","save":"Chekwaa","register":"Debanye aha","already":"Ị nwere akaụntụ?","need":"Ị bụ onye ọhụrụ na WonderLove?","send":"Zipu ozi","like":"Masị m","edit":"Dezie profaịlụ","no_people":"Enweghị profaịlụ ugbu a.","message":"Ozi","language":"Asụsụ","search":"Chọọ","age_from":"Afọ kacha nta","age_to":"Afọ kacha elu","any_country":"Obodo ọ bụla","report":"Kpesa","block":"Gbochie","delete":"Hichapụ akaụntụ","translate":"Tụgharịa"}
}

def db_conn():
    if "db" not in g:
        g.db = psycopg.connect(DATABASE_URL, row_factory=dict_row)
    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    # Create each table separately for PostgreSQL compatibility.
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
          id BIGSERIAL PRIMARY KEY,
          name TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, dob TEXT NOT NULL,
          sex TEXT NOT NULL CHECK(sex IN ('Male','Female')),
          country TEXT NOT NULL, looking_for TEXT NOT NULL DEFAULT 'Everyone',
          bio TEXT DEFAULT '', interests TEXT DEFAULT '', intentions TEXT DEFAULT '',
          photo TEXT DEFAULT '', language TEXT DEFAULT 'en',
          created_at TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS likes (
          id BIGSERIAL PRIMARY KEY,
          from_user BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          to_user BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          created_at TEXT NOT NULL, UNIQUE(from_user,to_user), CHECK(from_user != to_user)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS messages (
          id BIGSERIAL PRIMARY KEY,
          sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          recipient_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          body TEXT NOT NULL, created_at TEXT NOT NULL
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS blocks (
          blocker_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          blocked_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          PRIMARY KEY(blocker_id, blocked_id), CHECK(blocker_id != blocked_id)
        )""")
        db.execute("""CREATE TABLE IF NOT EXISTS reports (
          id BIGSERIAL PRIMARY KEY,
          reporter_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          reported_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          reason TEXT NOT NULL, created_at TEXT NOT NULL
        )""")

init_db()

def current_user():
    if "user_id" not in session:
        return None
    return db_conn().execute("SELECT * FROM users WHERE id=%s", (session["user_id"],)).fetchone()

@app.context_processor
def inject_globals():
    user = current_user()
    lang = (user["language"] if user else session.get("language", "en"))
    if lang not in LANGUAGES: lang = "en"
    return {"me": user, "langs": LANGUAGES, "lang": lang, "t": UI.get(lang, UI["en"])}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("Please log in to continue.")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def is_adult(dob):
    try:
        born = date.fromisoformat(dob)
        today = date.today()
        return (today.year - born.year - ((today.month, today.day) < (born.month, born.day))) >= 18
    except Exception:
        return False

def age_from_dob(dob):
    try:
        born = date.fromisoformat(dob); today = date.today()
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    except Exception:
        return None

def matched(db, a, b):
    return db.execute("SELECT 1 FROM likes WHERE from_user=%s AND to_user=%s", (a,b)).fetchone() and db.execute("SELECT 1 FROM likes WHERE from_user=%s AND to_user=%s", (b,a)).fetchone()

def is_blocked(db, a, b):
    return bool(db.execute("SELECT 1 FROM blocks WHERE (blocker_id=%s AND blocked_id=%s) OR (blocker_id=%s AND blocked_id=%s)", (a,b,b,a)).fetchone())

def introductory_count(db, sender, recipient):
    # Count messages sent by this member to this person before they match.
    return db.execute("SELECT COUNT(*) n FROM messages WHERE sender_id=%s AND recipient_id=%s", (sender,recipient)).fetchone()["n"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/language", methods=["POST"])
def set_language():
    code = request.form.get("language", "en")
    if code not in LANGUAGES: code = "en"
    session["language"] = code
    user = current_user()
    if user:
        db_conn().execute("UPDATE users SET language=%s WHERE id=%s", (code,user["id"]))
        db_conn().commit()
    return redirect(request.referrer or url_for("index"))

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()[:60]
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        confirm = request.form.get("confirm","")
        dob = request.form.get("dob","")
        sex = request.form.get("sex","")
        country = request.form.get("country","").strip()[:80]
        looking = request.form.get("looking_for","Everyone")
        if not name or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or not country:
            flash("Please enter a display name, valid email address, and country.")
        elif len(password) < 8:
            flash("Use a password with at least 8 characters.")
        elif password != confirm:
            flash("Your passwords do not match. Please check and try again.")
        elif sex not in ("Male","Female"):
            flash("Please select Male or Female.")
        elif looking not in ("Male","Female","Everyone"):
            flash("Please select who you would like to meet.")
        elif not is_adult(dob):
            flash("WonderLove is for adults aged 18 and over. Please enter a valid date of birth.")
        else:
            db = db_conn()
            try:
                cur = db.execute("INSERT INTO users (name,email,password_hash,dob,sex,country,looking_for,language,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (name,email,generate_password_hash(password),dob,sex,country,looking,session.get("language","en"),datetime.utcnow().isoformat()))
                new_user_id = cur.fetchone()["id"]
                db.commit()
                session.clear(); session["user_id"] = new_user_id
                flash("Welcome to WonderLove! Your account was created.")
                return redirect(url_for("profile"))
            except psycopg.IntegrityError:
                flash("That email address is already registered. Please log in instead.")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        user = db_conn().execute("SELECT * FROM users WHERE email=%s", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear(); session["user_id"] = user["id"]
            flash("Welcome back!")
            return redirect(url_for("discover"))
        flash("Email or password is incorrect.")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("index"))

@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    db=db_conn(); user=current_user()
    if request.method=="POST":
        name=request.form.get("name","").strip()[:60]
        country=request.form.get("country","").strip()[:80]
        bio=request.form.get("bio","").strip()[:500]
        interests=request.form.get("interests","").strip()[:300]
        intentions=request.form.get("intentions","").strip()[:200]
        looking=request.form.get("looking_for","Everyone")
        language=request.form.get("language","en")
        if looking not in ("Male","Female","Everyone"): looking="Everyone"
        if language not in LANGUAGES: language="en"
        photo=user["photo"]
        f=request.files.get("photo")
        if f and f.filename:
            filename=secure_filename(f.filename)
            ext=filename.rsplit(".",1)[-1].lower() if "." in filename else ""
            if ext not in ALLOWED_EXTENSIONS:
                flash("Please upload a JPG, PNG, or WEBP image.")
                return redirect(url_for("profile"))
            filename=f"user_{user['id']}_{secrets.token_hex(6)}.{ext}"
            f.save(os.path.join(UPLOAD_FOLDER,filename))
            photo="uploads/"+filename
        if not name or not country:
            flash("Display name and country are required.")
        else:
            db.execute("UPDATE users SET name=%s,country=%s,bio=%s,interests=%s,intentions=%s,looking_for=%s,language=%s,photo=%s WHERE id=%s",
                (name,country,bio,interests,intentions,looking,language,photo,user["id"]))
            db.commit(); session["language"]=language
            flash("Your profile has been saved.")
            return redirect(url_for("profile"))
    user=current_user()
    return render_template("profile.html", user=user, age=age_from_dob(user["dob"]))

@app.route("/discover")
@login_required
def discover():
    db=db_conn(); me=current_user()
    q=request.args.get("q","").strip()[:80]
    country=request.args.get("country","").strip()[:80]
    min_age=request.args.get("min_age","18")
    max_age=request.args.get("max_age","99")
    users=db.execute("SELECT * FROM users WHERE id != %s ORDER BY created_at DESC", (me["id"],)).fetchall()
    result=[]
    for u in users:
        if is_blocked(db, me["id"], u["id"]): continue
        if me["looking_for"] not in ("Everyone",u["sex"]): continue
        if u["looking_for"] not in ("Everyone",me["sex"]): continue
        age=age_from_dob(u["dob"])
        try:
            if age < max(18,int(min_age)) or age > min(99,int(max_age)): continue
        except Exception: pass
        if country and country.lower() not in u["country"].lower(): continue
        if q and q.lower() not in (u["name"]+" "+u["bio"]+" "+u["interests"]+" "+u["country"]).lower(): continue
        result.append({"user":u,"age":age,"liked":bool(db.execute("SELECT 1 FROM likes WHERE from_user=%s AND to_user=%s",(me["id"],u["id"])).fetchone()),"matched":bool(matched(db,me["id"],u["id"]))})
    return render_template("discover.html", profiles=result, q=q, country=country, min_age=min_age, max_age=max_age)

@app.route("/like/<int:user_id>", methods=["POST"])
@login_required
def like(user_id):
    db=db_conn(); me=current_user()
    if user_id==me["id"]: abort(400)
    target=db.execute("SELECT * FROM users WHERE id=%s", (user_id,)).fetchone()
    if not target: abort(404)
    if is_blocked(db,me["id"],user_id):
        flash("You cannot interact with this member.")
        return redirect(url_for("discover"))
    db.execute("INSERT INTO likes (from_user,to_user,created_at) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",(me["id"],user_id,datetime.utcnow().isoformat()))
    db.commit()
    if matched(db,me["id"],user_id):
        flash("It's a match! You can now chat freely. ❤️")
    else:
        flash("Like sent. If they like you back, you'll match!")
    return redirect(request.referrer or url_for("discover"))

@app.route("/matches")
@login_required
def matches():
    db=db_conn(); me=current_user()
    rows=db.execute("""SELECT u.* FROM likes l JOIN users u ON u.id=l.to_user
       WHERE l.from_user=%s AND EXISTS (SELECT 1 FROM likes x WHERE x.from_user=u.id AND x.to_user=%s)
       ORDER BY u.name""",(me["id"],me["id"])).fetchall()
    people=[{"user":u,"age":age_from_dob(u["dob"])} for u in rows if not is_blocked(db,me["id"],u["id"])]
    return render_template("matches.html", profiles=people)

@app.route("/messages")
@login_required
def message_list():
    db=db_conn(); me=current_user()
    rows=db.execute("""SELECT u.* FROM users u WHERE u.id != %s AND
      (EXISTS(SELECT 1 FROM messages m WHERE (m.sender_id=%s AND m.recipient_id=u.id) OR (m.sender_id=u.id AND m.recipient_id=%s)))
      ORDER BY u.name""",(me["id"],me["id"],me["id"])).fetchall()
    people=[{"user":u,"age":age_from_dob(u["dob"])} for u in rows if not is_blocked(db,me["id"],u["id"])]
    return render_template("messages.html", profiles=people)

@app.route("/chat/<int:user_id>", methods=["GET","POST"])
@login_required
def chat(user_id):
    db=db_conn(); me=current_user()
    if user_id==me["id"]: abort(400)
    other=db.execute("SELECT * FROM users WHERE id=%s", (user_id,)).fetchone()
    if not other: abort(404)
    if is_blocked(db,me["id"],user_id):
        flash("This conversation is unavailable.")
        return redirect(url_for("discover"))
    is_match=bool(matched(db,me["id"],user_id))
    if request.method=="POST":
        body=request.form.get("body","").strip()
        count=int(introductory_count(db,me["id"],user_id))
        if not body:
            flash("Please write a message first.")
        elif len(body)>1000:
            flash("Messages must be 1,000 characters or fewer.")
        elif not is_match and count>=3:
            flash("You've used your 3 introductory messages with this person. If you both like each other, you can continue chatting.")
        else:
            db.execute("INSERT INTO messages (sender_id,recipient_id,body,created_at) VALUES (%s,%s,%s,%s)",(me["id"],user_id,body,datetime.utcnow().isoformat()))
            db.commit()
            return redirect(url_for("chat",user_id=user_id))
    rows=db.execute("""SELECT m.*,u.name sender_name FROM messages m JOIN users u ON u.id=m.sender_id
      WHERE (m.sender_id=%s AND m.recipient_id=%s) OR (m.sender_id=%s AND m.recipient_id=%s)
      ORDER BY m.id""",(me["id"],user_id,user_id,me["id"])).fetchall()
    can_send=is_match or introductory_count(db,me["id"],user_id)<3
    return render_template("chat.html", other=other, age=age_from_dob(other["dob"]), messages=rows, is_match=is_match, can_send=can_send)

@app.route("/member/<int:user_id>")
@login_required
def member(user_id):
    db=db_conn(); me=current_user()
    u=db.execute("SELECT * FROM users WHERE id=%s", (user_id,)).fetchone()
    if not u: abort(404)
    if is_blocked(db,me["id"],user_id):
        flash("This profile is unavailable.")
        return redirect(url_for("discover"))
    return render_template("member.html", user=u, age=age_from_dob(u["dob"]), liked=bool(db.execute("SELECT 1 FROM likes WHERE from_user=%s AND to_user=%s",(me["id"],user_id)).fetchone()), matched=bool(matched(db,me["id"],user_id)))

@app.route("/block/<int:user_id>", methods=["POST"])
@login_required
def block(user_id):
    db=db_conn(); me=current_user()
    if user_id != me["id"]:
        db.execute("INSERT INTO blocks(blocker_id,blocked_id) VALUES (%s,%s) ON CONFLICT DO NOTHING",(me["id"],user_id))
        db.commit()
    flash("Member blocked.")
    return redirect(url_for("discover"))

@app.route("/report/<int:user_id>", methods=["POST"])
@login_required
def report(user_id):
    db=db_conn(); me=current_user()
    reason=request.form.get("reason","Safety concern").strip()[:300] or "Safety concern"
    if user_id != me["id"]:
        db.execute("INSERT INTO reports(reporter_id,reported_id,reason,created_at) VALUES (%s,%s,%s,%s)",(me["id"],user_id,reason,datetime.utcnow().isoformat()))
        db.commit()
    flash("Thank you. Your report has been recorded.")
    return redirect(url_for("discover"))

@app.route("/delete-account", methods=["GET","POST"])
@login_required
def delete_account():
    db=db_conn(); me=current_user()
    if request.method=="POST":
        db.execute("DELETE FROM users WHERE id=%s", (me["id"],)); db.commit()
        session.clear(); flash("Your account has been deleted.")
        return redirect(url_for("index"))
    return render_template("delete_account.html")

@app.route("/privacy")
def privacy(): return render_template("legal.html", title="Privacy", body="WonderLove should only collect information needed to operate accounts and matching. Never share your password. Before public launch, the owner must review and publish a privacy policy explaining hosting, retention, contact details, and any third-party services used.")

@app.route("/terms")
def terms(): return render_template("legal.html", title="Terms", body="WonderLove is intended for adults aged 18 and older. Be respectful, do not harass or impersonate others, and do not use the service for scams or spam. Users can block and report members. Before public launch, the owner must review these terms and add accurate operator contact details.")

@app.route("/health")
def health(): return {"status":"ok","app":"WonderLove"}

@app.errorhandler(413)
def too_large(error):
    flash("That image is too large. Please choose an image under 3 MB.")
    return redirect(url_for("profile"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
