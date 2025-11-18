from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, url_for
import os
import bcrypt
import random
import datetime
from flask_mail import Mail, Message
from flask_session import Session
import emailbase as em  # tu módulo para acceder a la BD
from functools import wraps
from flask import session, redirect
from fpdf import FPDF
from flask import jsonify
from config import Config

Config.validate()  # Validar al inicio





from emailbase import Email

if __name__ == "__main__":
    correo = Email()
    usuarios = correo.listarusers()
    print("Lista de usuarios:", usuarios)


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('authenticated'):
            return redirect('/home')  # redirige al login si no está autenticado
        return f(*args, **kwargs)
    return decorated_function


# ---------------- CONFIGURACIÓN ----------------
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = Config.MAIL_USERNAME
app.config['MAIL_PASSWORD'] = Config.MAIL_PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = Config.MAIL_DEFAULT_SENDER

mail = Mail(app)

# Configuración de sesión
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = False
Session(app)

# ---------------- RUTAS ----------------
@app.route('/')
def index():
    return redirect('/home')

# --- LOGIN ---
@app.route('/home', methods=['GET', 'POST'])
def home():
    session.clear()  # limpia cualquier dato anterior

    if session.get('authenticated'):# ya está autenticado
        return redirect('/fichaje')# redirige a fichaje

    if request.method == 'POST':
        # Procesar login
        username = request.form.get('username')
        password = request.form.get('password')
        # Validar campos
        if not username or not password:
            return render_template('home.html', error="Por favor, completa todos los campos")
        # Verificar credenciales
        try:
            cursor = em.database.cursor()
            sql = "SELECT password_hash, email, nombre, rol FROM usuarios WHERE username = %s"
            cursor.execute(sql, (username,))
            user_data = cursor.fetchone()
            cursor.close()
            # user_data = (password_hash, email, nombre, rol) o None
            if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data[0].encode('utf-8')):
                session['authenticated'] = True
                session['current_user'] = username
                session['rol'] = user_data[3]
                session['user_email'] = user_data[1]
                session['user_name'] = user_data[2]
                
                if session['rol'] == 'admin':
                    return redirect('/admin')  # Redirige a la página de administración si es admin
                return redirect('/fichaje')
            else:
                return render_template('home.html', error="Credenciales inválidas")

        except Exception as e:
            print(f"Error en login: {e}")
            return render_template('home.html', error="Error en el sistema.")

    return render_template('home.html')

@app.route('/admin')
@login_required
def admin():
    if session.get('rol') != 'admin':
        return redirect('/home')

    username = session.get('current_user')
    now = datetime.datetime.now()
    cursor = em.database.cursor()
    
    # Obtener último registro
    cursor.execute("""
        SELECT fecha 
        FROM registro_fichajes 
        WHERE username = %s 
        ORDER BY fecha DESC 
        LIMIT 1
    """, (username,))
    ultimo = cursor.fetchone()

    # Insertar nuevo registro solo si no hay registro o pasó más de 1 minuto
    if not ultimo:
        cursor.execute(
            "INSERT INTO registro_fichajes (username, fecha) VALUES (%s, %s)",
            (username, now)
        )
        em.database.commit()

    # Obtener todos los registros
    cursor.execute("SELECT id, username, fecha FROM public.registro_fichajes ORDER BY fecha DESC;")
    registros = cursor.fetchall()
    cursor.close()

    return render_template('admin.html', registros=registros, username=username)


@app.route('/registro_accesos')
@login_required
def registro_accesos():
    if not session.get('authenticated'):
        return redirect('/home')

    if session.get('rol') != 'admin':
        return redirect('/home')

    cursor = em.database.cursor()
    sql = """
        SELECT id,username,fecha FROM public.registro_fichajes ORDER BY fecha DESC; 
        """
    cursor.execute(sql)
    registros = cursor.fetchall()
    cursor.close()

    return render_template('registro_accesos.html', registros=registros, username=session.get('current_user'))




@app.route('/tipos')
@login_required
def tipos():
    if not session.get('authenticated'):
        return redirect('/home')
    if session.get('rol') != 'admin':
        return redirect('/home')

    cursor = em.database.cursor()
    sql = "SELECT id,nombre FROM public.infotipo ORDER BY nombre ASC;"
    cursor.execute(sql)
    tipos = cursor.fetchall()
    cursor.close()

    return render_template('tipos.html', tipos=tipos, username=session.get('current_user'))

#Buscador de tipos.
@app.route('/api/tipos', methods=['GET'])
@login_required
def api_tipos():
    if not session.get('authenticated') or session.get('rol') != 'admin':
        return jsonify({'error': 'No autorizado'}), 403

    filtro = request.args.get('q', '').strip().lower()
    cursor = em.database.cursor()

    if filtro:
        sql = "SELECT id, nombre FROM public.infotipo WHERE LOWER(nombre) LIKE %s ORDER BY id ASC;"
        cursor.execute(sql, (f'%{filtro}%',))
    else:
        sql = "SELECT id, nombre FROM public.infotipo ORDER BY id ASC;"
        cursor.execute(sql)

    tipos = cursor.fetchall()
    cursor.close()

    # Convertir a formato JSON
    data = [{'id': t[0], 'nombre': t[1]} for t in tipos]
    return jsonify(data)



@app.route('/agregar', methods=['POST'])
@login_required
def agregar_tipo():
    if not session.get('authenticated'):
        return redirect('/home')
    if session.get('rol') != 'admin':
        return redirect('/home')

    nombre = request.form['nombre']
    cursor = em.database.cursor()
    sql = "INSERT INTO public.infotipo (nombre) VALUES (%s);"
    cursor.execute(sql, (nombre,))
    em.database.commit()
    cursor.close()
    return redirect(url_for('tipos'))


@app.route('/actualizar/<int:id>', methods=['POST'])
def actualizar_tipo(id):
    nombre = request.form['nombre']
    cursor = em.database.cursor()
    sql = "UPDATE public.infotipo SET nombre = %s WHERE id = %s;"
    cursor.execute(sql, (nombre, id))
    em.database.commit()
    cursor.close()
    return redirect(url_for('tipos'))

@app.route('/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_tipo(id):
    if not session.get('authenticated') or session.get('rol') != 'admin':
        return redirect('/home')

    cursor = em.database.cursor()
    sql = "DELETE FROM public.infotipo WHERE id = %s;"
    cursor.execute(sql, (id,))
    em.database.commit()
    cursor.close()

    return redirect(url_for('tipos'))


    


###########CABECERA##########


@app.route('/cabecera')
def cabeceras():
    print("Accediendo a /cabecera")
    if not session.get('authenticated'):
        return redirect('/home')
    if session.get('rol') != 'admin':
        return redirect('/home')

    cursor = em.database.cursor()
    sql = """
        SELECT 
        infocab.referencia,
        infocab.id_tipo,
        infotipo.nombre
        FROM public.infocab
        INNER JOIN public.infotipo
        ON infocab.id_tipo = infotipo.id
        ORDER BY infocab.referencia ASC;
    """

    cursor.execute(sql)
    cabeceras = cursor.fetchall()
    cursor.close()

    cursor = em.database.cursor()
    cursor.execute("SELECT * FROM public.infocab;")
    rows = cursor.fetchall()
    print("Infocab:", rows)

    cursor.execute("SELECT id, nombre FROM public.infotipo ORDER BY id ASC;")
    tipos = cursor.fetchall()
    cursor.close()

    return render_template('cabecera.html', tipos=tipos, cabeceras=cabeceras, username=session.get('current_user'))


@app.route('/api/cabeceras', methods=['GET'])
@login_required
def api_cabeceras():
    if not session.get('authenticated') or session.get('rol') != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    
    filtro = request.args.get('q', '').strip().lower()
    cursor = em.database.cursor()

    if filtro:
        sql = """
            SELECT 
                infocab.referencia, infocab.id_tipo, infotipo.nombre
            FROM public.infocab
            INNER JOIN public.infotipo ON infocab.id_tipo = infotipo.id
            WHERE LOWER(infocab.referencia) LIKE %s OR LOWER(infotipo.nombre) LIKE %s
            ORDER BY infocab.id_tipo ASC;
        """
        cursor.execute(sql, (f'%{filtro}%', f'%{filtro}%'))
    else:
        sql = """
            SELECT 
                infocab.referencia, infocab.id_tipo, infotipo.nombre
            FROM public.infocab
            INNER JOIN public.infotipo ON infocab.id_tipo = infotipo.id
            ORDER BY infocab.id_tipo ASC;
        """
        cursor.execute(sql)
    cabeceras = cursor.fetchall()
    cursor.close()
    data = [{
        'referencia': c[0],
        'id_tipo': c[1],
        'tipo_nombre': c[2]
    } for c in cabeceras]
    return jsonify(data)

@app.route('/actualizar_cab/<referencia>', methods=['POST'])
def actualizar_cab(referencia):
    tipo = request.form.get('tipo')
    print(f"Referencia: {referencia}, Tipo: {tipo}")
    cursor = em.database.cursor()
    sql = "UPDATE public.infocab SET id_tipo = %s WHERE referencia = %s;"
    cursor.execute(sql, (tipo, referencia))
    em.database.commit()
    cursor.close()
    return redirect(url_for('cabeceras'))

@app.route('/eliminar_cab/<referencia>', methods=['POST'])
def eliminar_cab(referencia):
    print(f"Referencia del Eliminado: {referencia}")
    cursor = em.database.cursor()
    sql = "DELETE FROM public.infocab WHERE referencia = %s;"
    cursor.execute(sql, (referencia,))
    em.database.commit()
    cursor.close()
    return redirect(url_for('cabeceras'))

'''
@app.route('/guardar/<int:id>', methods=['POST'])


'''
@app.route('/agregar_cab', methods=['POST'])
def agregar_cab():
    if not session.get('authenticated') or session.get('rol') != 'admin':
        return jsonify({'error': 'No autorizado'}), 403
    tipo = request.form.get('tipo')
    referencia = request.form.get('referencia')
    print(f"Referencia: {referencia}, Tipo: {tipo}")
    cursor = em.database.cursor()
    sql= "SELECT infocab.referencia FROM public.infocab"
    cursor.execute(sql)
    em.database.commit()
    referencias = cursor.fetchall()
    print(referencias)
    
    for ref in referencias:
        if ref[0] == referencia:
            return redirect(url_for('cabeceras', error=f"La referencia {referencia} ya está registrada."))
 
    
    sql= """
            INSERT INTO public.infocab (referencia,id_tipo)
            VALUES (%s,%s)
        """
    cursor.execute(sql,(referencia,tipo))
    em.database.commit()
    cursor.close()
    return redirect(url_for('cabeceras'))



    

###########DETALLES##########


@app.route('/detalle')
def detalles():
    print("Accediendo a /detalles")
    if not session.get('authenticated') or session.get('rol') != 'admin':
        return redirect('/home')

    cursor = em.database.cursor()
    try:
        sql = """
            SELECT 
            infodet.id,
            infodet.id_infocab,
            infodet.referencia,
            infodet.desc1,
            infodet.desc2,
            infodet.notas,
            infocab.referencia
            FROM public.infodet
            INNER JOIN public.infocab 
            ON infodet.id_infocab = infocab.id
            ORDER BY infocab.referencia ASC;
        """
        cursor.execute(sql)
        detalles = cursor.fetchall()

        sql = "SELECT id, referencia FROM public.infocab ORDER BY id ASC"
        cursor.execute(sql)
        referencias = cursor.fetchall()

    except Exception as e:
        em.database.rollback()  # <-- esto reinicia la transacción
        cursor.close()
        raise e

    cursor.close()


    return render_template('detalle.html', detalles=detalles, username=session.get('current_user'), referencias=referencias)


##Buscador de detalles.

@app.route('/api/detalles', methods=['GET'])
@login_required
def api_detalles():
    if not session.get('authenticated') or session.get('rol') != 'admin':
        return jsonify({'error': 'No autorizado'}), 403

    filtro = request.args.get('q', '').strip().lower()
    cursor = em.database.cursor()

    if filtro:
        sql = """
            SELECT 
                infodet.id,
                infodet.id_infocab,
                infodet.referencia,
                infodet.desc1,
                infodet.desc2,
                infodet.notas,
                infocab.referencia
            FROM public.infodet
            INNER JOIN public.infocab ON infodet.id_infocab = infocab.id
            WHERE LOWER(infocab.referencia) LIKE %s OR LOWER(infodet.referencia) LIKE %s
            ORDER BY infocab.referencia ASC;
        """
        cursor.execute(sql, (f'%{filtro}%', f'%{filtro}%'))
    else:
        sql = """
            SELECT 
                infodet.id, infodet.id_infocab, infodet.referencia,
                infodet.desc1, infodet.desc2, infodet.notas, infocab.referencia
            FROM public.infodet
            INNER JOIN public.infocab ON infodet.id_infocab = infocab.id
            ORDER BY infocab.referencia ASC;
        """
        cursor.execute(sql)

    detalles = cursor.fetchall()
    cursor.close()

    data = [{
        'id': d[0],
        'id_infocab': d[1],
        'referencia': d[2],
        'desc1': d[3],
        'desc2': d[4],
        'notas': d[5],
        'infocab_ref': d[6]
    } for d in detalles]

    return jsonify(data)


@app.route('/actualizar_det/<int:id>', methods=['POST'])
def actualizar_det(id):
    try:
        # Obtener datos del formulario
        id_infocab_ref = request.form.get('id_infocab')
        referencia = request.form.get('referencia')
        desc1 = request.form.get('desc1')
        desc2 = request.form.get('desc2')
        notas = request.form.get('notas')

        cursor = em.database.cursor()
        cursor.execute("SELECT id, referencia FROM public.infocab WHERE referencia = %s;", (id_infocab_ref,))
        infocab_data = cursor.fetchone()
        cursor.close()

        if infocab_data:
            id_infocab_real = infocab_data[0]
        else:
            print(f"⚠️ No se encontró un infocab con referencia {id_infocab_ref}")
            id_infocab_real = None

        if id_infocab_real is None:
            return f"Error: No existe un infocab con referencia '{id_infocab_ref}'", 400

        # Actualizar los datos en la tabla infodet
        cursor = em.database.cursor()
        sql = """
            UPDATE public.infodet 
            SET id_infocab = %s, referencia = %s, desc1 = %s, desc2 = %s, notas = %s
            WHERE id = %s;
        """
        cursor.execute(sql, (id_infocab_real, referencia, desc1, desc2, notas, id))
        em.database.commit()
        cursor.close()

        print("Registro actualizado correctamente.")
        return redirect(url_for('detalles'))

    except Exception as e:
        em.database.rollback()
        print(f"Error al actualizar el registro: {e}")
        return f"Error al actualizar el registro: {e}", 500






@app.route('/eliminar_det/<id>', methods=['POST'])
def eliminar_det(id):
    print(f"ID del Eliminado: {id}")
    cursor = em.database.cursor()
    sql = "DELETE FROM public.infodet WHERE id = %s;"
    cursor.execute(sql, (id,))
    em.database.commit()
    cursor.close()
    return redirect(url_for('detalles'))

@app.route('/agregar_det', methods=['POST'])
def agregar_det():
    if not session.get('authenticated') or session.get('rol') != 'admin':
        return redirect('/home')

    try:
        id_infocab_real = int(request.form.get('id_infocab'))
        referencia = request.form.get('referencia')
        desc1 = request.form.get('desc1')
        desc2 = request.form.get('desc2')
        notas = request.form.get('notas')

        cursor = em.database.cursor()
        sql = """
            INSERT INTO public.infodet (id_infocab, referencia, desc1, desc2, notas)
            VALUES (%s, %s, %s, %s, %s);
        """
        cursor.execute(sql, (id_infocab_real, referencia, desc1, desc2, notas))
        em.database.commit()
        cursor.close()

        return redirect(url_for('detalles'))

    except Exception as e:
        em.database.rollback()
        print(f"Error al agregar el registro: {e}")
        return f"Error al agregar el registro: {e}", 500





from flask import send_file

@app.route('/admin/export/pdf')
@login_required
def export_pdf():
    if not session.get('authenticated'):
        return redirect('/home')
    if session.get('rol') != 'admin':
        return redirect('/home')

    cursor = em.database.cursor()
    sql = "SELECT id,username,fecha FROM public.registro_fichajes ORDER BY fecha DESC;"
    cursor.execute(sql)
    registros = cursor.fetchall()
    cursor.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Registro de Fichajes", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(40, 10, "ID", 1)
    pdf.cell(60, 10, "Username", 1)
    pdf.cell(60, 10, "Fecha", 1)
    pdf.ln()

    for r in registros:
        pdf.cell(40, 10, str(r[0]), 1)
        pdf.cell(60, 10, r[1], 1)
        pdf.cell(60, 10, r[2].strftime("%Y-%m-%d %H:%M:%S"), 1)
        pdf.ln()

    output_dir = "static/pdfs"
    os.makedirs(output_dir, exist_ok=True)
    pdf_output = os.path.join(output_dir, "registro_fichajes.pdf")
    pdf.output(pdf_output)

    # 👇 En lugar de redirigir, enviamos el archivo directamente
    return send_file(pdf_output, as_attachment=True, download_name="registro_fichajes.pdf")




# --- fichaje (solo prueba de login exitoso) ---
@app.route('/fichaje')
@login_required
def fichaje():
    username = session.get('current_user')  # debe ir primero
    now = datetime.datetime.now()
    print("Usuario fichando:", username)
    print("Hora:", now)

    cursor = em.database.cursor()

    # Insertar siempre un registro de acceso
    cursor.execute(
        "INSERT INTO registro_fichajes (username, fecha) VALUES (%s, %s)",
        (username, now)
    )

    # Actualizar última fecha en usuarios
    cursor.execute(
        "UPDATE usuarios SET ultima_fecha = %s WHERE username = %s",
        (now, username)
    )

    em.database.commit()
    cursor.close()

    return render_template('fichaje.html', username=username)



@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        user_email = request.form['email']
        password = request.form['password']
        name = request.form['name']
        username = request.form['username']

        if not all([user_email, password, name, username]):
            return render_template('registro.html', error="Todos los campos son obligatorios")

        if len(password) < 6:
            return render_template('registro.html', error="La contraseña debe tener al menos 6 caracteres")

        try:
            '''
            cursor = em.database.cursor()
            sql = "SELECT username FROM usuarios WHERE username = %s"
            cursor.execute(sql, (username,))
            if cursor.fetchone():
                return render_template('registro.html', error="El nombre de usuario ya está en uso")
            cursor.close()
        '''
            email_manager = email()
            usuarios = email_manager.listarusers() # lista de emails registrados
            if user_email in usuarios:
                return render_template('registro.html', error="El usuario ya está registrado")
            # Generar OTP y hash de contraseña
            otp = random.randint(100000, 999999) #código de verificación temporal
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()) #crear un hash seguro de la contraseña del usuario.

            session['email'] = user_email
            session['username'] = username
            session['name'] = name
            session['password_hash'] = password_hash.decode('utf-8')
            session['otp'] = otp

            #isoformat para serializar datetime (ponerlo como cadena de texto)
            session['otp_expiry'] = (datetime.datetime.now() + datetime.timedelta(minutes=5)).isoformat()# Expira en 5 minutos
            
            
            # usa el parámetro recipients porque así lo requiere Flask-Mail para enviar un correo. Vamos a explicarlo bien.
            msg = Message('Tu código de acceso',
                          recipients=[user_email]) 
            msg.body = f'Bienvenido {name}!\nTu código de verificación es: {otp}'
            mail.send(msg)

            return redirect('/verify')

        except Exception as e:
            print(f"Error en registro: {e}")
            return render_template('registro.html', error="Error en el sistema. Intenta de nuevo.")

    return render_template('registro.html')

# --- VERIFICAR OTP ---
@app.route('/verify', methods=['GET', 'POST'])
def verify():
    if request.method == 'POST':
        user_otp = request.form['otp']# OTP ingresado por el usuario
        stored_otp = session.get('otp')# OTP almacenado en la sesión
        expiry_str = session.get('otp_expiry')# Caducidad del OTP en la sesión

        print(f"Stored OTP: {stored_otp}, Expiry: {expiry_str}")
        
        if not stored_otp or not expiry_str:# OTP o caducidad no existen en la sesión
            return render_template('verify.html', error="Código expirado. Vuelve a registrarte.")

        expiry = datetime.datetime.fromisoformat(expiry_str)# convertir cadena a datetime
        if datetime.datetime.now() > expiry:
            return render_template('verify.html', error="El código ha expirado.")

        if int(user_otp) == stored_otp:
            try:
                cursor = em.database.cursor()
                sql = """
                    INSERT INTO usuarios (email, username, nombre, password_hash, fecha_creacion)
                    VALUES (%s, %s, %s, %s, %s)
                """

                data = (
                    session.get('email'),
                    session.get('username'),
                    session.get('username'),
                    session.get('password_hash'),
                    datetime.datetime.now()
                )
                cursor = em.database.cursor()
                cursor.execute(sql, data)
                em.database.commit()
                cursor.close()
                print("Usuario insertado correctamente")

                session['authenticated'] = True
                session['current_user'] = session.get('username')
                session['user_email'] = session.get('email')
                session['user_name'] = session.get('name')

                for key in ['email', 'username', 'name', 'password_hash', 'otp', 'otp_expiry']:
                    session.pop(key, None)

                return redirect('/fichaje')

            except Exception as e:
                print(f"Error creando usuario: {e}")
                return render_template('verify.html', error="Error creando usuario.")
        else:
            return render_template('verify.html', error="Código incorrecto")

    return render_template('verify.html')

# --- OLVIDAR CONTRASEÑA ---
@app.route('/olvidar_contrasenya', methods=['GET', 'POST'])
def recuperar_contrasenya():
    if request.method == 'POST':
        user_email = request.form['email']

        try:
            email_manager = email()
            usuarios = email_manager.listarusers()

            if user_email not in usuarios:
                return render_template('olvidar_contrasenya.html', error="El email no está registrado")

            otp = random.randint(100000, 999999)
            session['reset_email'] = user_email
            session['reset_otp'] = otp
            session['reset_otp_expiry'] = (datetime.datetime.now() + datetime.timedelta(minutes=5)).isoformat()

            msg = Message('Recuperar contraseña',
                          recipients=[user_email])
            msg.body = f'Tu código de recuperación es: {otp}'
            mail.send(msg)

            return redirect('/verificar_recuperacion')

        except Exception as e:
            print(f"Error en recuperar_contrasenya: {e}")
            return render_template('olvidar_contrasenya.html', error="Error en el sistema.")

    return render_template('olvidar_contrasenya.html')

# --- VERIFICAR OTP RECUPERACIÓN ---
@app.route('/verificar_recuperacion', methods=['GET', 'POST'])
def verificar_recuperacion():
    if request.method == 'POST':
        user_otp = request.form['otp']
        stored_otp = session.get('reset_otp')
        expiry_str = session.get('reset_otp_expiry')

        if not stored_otp or not expiry_str:
            return render_template('verificar_recuperacion.html', error="Código expirado. Solicita uno nuevo.")

        expiry = datetime.datetime.fromisoformat(expiry_str)
        if datetime.datetime.now() > expiry:
            return render_template('verificar_recuperacion.html', error="El código ha expirado.")

        if int(user_otp) == stored_otp:
            return redirect('/nueva_contrasenya')
        else:
            return render_template('verificar_recuperacion.html', error="Código incorrecto")

    return render_template('verificar_recuperacion.html')

# --- NUEVA CONTRASEÑA ---
@app.route('/nueva_contrasenya', methods=['GET', 'POST'])
def nueva_contrasenya():
    if request.method == 'POST':
        nueva_password = request.form['password']
        confirmar_password = request.form['confirm_password']

        if nueva_password != confirmar_password:
            return render_template('nueva_contrasenya.html', error="Las contraseñas no coinciden")

        if len(nueva_password) < 6:
            return render_template('nueva_contrasenya.html', error="Debe tener al menos 6 caracteres")

        reset_email = session.get('reset_email')
        if not reset_email:
            return redirect('/olvidar_contrasenya')

        password_hash = bcrypt.hashpw(nueva_password.encode('utf-8'), bcrypt.gensalt())

        try:
            cursor = em.database.cursor()
            sql = "UPDATE usuarios SET password_hash = %s WHERE email = %s"
            cursor.execute(sql, (password_hash.decode('utf-8'), reset_email))
            em.database.commit()
            cursor.close()

            for key in ['reset_email', 'reset_otp', 'reset_otp_expiry']:
                session.pop(key, None)

            return render_template('nueva_contrasenya.html', success="Contraseña actualizada correctamente.")
        except Exception as e:
            print(f"Error actualizando contraseña: {e}")
            return render_template('nueva_contrasenya.html', error="Error al actualizar la contraseña.")

    return render_template('nueva_contrasenya.html')


# --- LOGOUT ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/home')


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=False)
