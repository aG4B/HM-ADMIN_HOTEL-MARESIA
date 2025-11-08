import sqlite3
from flask import Flask, render_template, request, url_for, redirect, send_file, Response, session, flash
import datetime
import uuid
import qrcode
import io
import csv
from functools import wraps

app = Flask(__name__)
app.secret_key = 'keyuni9hotelmaresia' 

def get_db_connection():
    """Cria uma conexão com o banco de dados."""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'HMADMIN' and password == 'UNI9HM':
            session['logged_in'] = True
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Credenciais inválidas. Tente novamente.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    flash('Você foi desconectado.', 'success')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = get_db_connection()
    estadias_ativas = conn.execute("""
        SELECT
            e.id, h.nome_completo, q.numero, e.data_checkin, e.data_checkout
        FROM estadias e
        JOIN hospedes h ON e.id_hospede = h.id
        JOIN quartos q ON e.id_quarto = q.id
        WHERE e.status_estadia = 'Ativa' ORDER BY e.data_checkin DESC
    """).fetchall()
    conn.close()
    return render_template('index.html', estadias=estadias_ativas)

@app.route('/quartos', methods=('GET', 'POST'))
@login_required
def quartos():
    conn = get_db_connection()
    if request.method == 'POST':
        numero = request.form['numero']
        tipo = request.form['tipo']
        conn.execute('INSERT INTO quartos (numero, tipo) VALUES (?, ?)', (numero, tipo))
        conn.commit()
        conn.close()
        return redirect(url_for('quartos'))
    quartos_db = conn.execute('SELECT * FROM quartos ORDER BY numero').fetchall()
    conn.close()
    return render_template('quartos.html', quartos=quartos_db)

@app.route('/hospedes', methods=('GET', 'POST'))
@login_required
def hospedes():
    conn = get_db_connection()
    if request.method == 'POST':
        nome = request.form['nome_completo']
        documento = request.form['documento']
        conn.execute('INSERT INTO hospedes (nome_completo, documento) VALUES (?, ?)', (nome, documento))
        conn.commit()
        conn.close()
        return redirect(url_for('hospedes'))
    hospedes_db = conn.execute('SELECT * FROM hospedes ORDER BY nome_completo').fetchall()
    conn.close()
    return render_template('hospedes.html', hospedes=hospedes_db)

@app.route('/checkin', methods=('GET', 'POST'))
@login_required
def checkin():
    conn = get_db_connection()
    if request.method == 'POST':
        id_hospede, id_quarto, data_checkout = request.form['id_hospede'], request.form['id_quarto'], request.form['data_checkout']
        chave_digital = str(uuid.uuid4())
        conn.execute('INSERT INTO estadias (id_hospede, id_quarto, data_checkout, chave_digital) VALUES (?, ?, ?, ?)',
                     (id_hospede, id_quarto, data_checkout, chave_digital))
        conn.execute('UPDATE quartos SET status = ? WHERE id = ?', ('Ocupado', id_quarto))
        conn.commit()
        conn.close()
        flash("Check-in realizado com sucesso!", 'success')
        return redirect(url_for('index'))
    quartos_disponiveis = conn.execute("SELECT * FROM quartos WHERE status = 'Disponivel' ORDER BY numero").fetchall()
    todos_hospedes = conn.execute('SELECT * FROM hospedes ORDER BY nome_completo').fetchall()
    conn.close()
    return render_template('checkin.html', quartos=quartos_disponiveis, hospedes=todos_hospedes)

@app.route('/checkout/<int:id_estadia>')
@login_required
def checkout(id_estadia):
    conn = get_db_connection()
    estadia = conn.execute('SELECT id_quarto FROM estadias WHERE id = ?', (id_estadia,)).fetchone()
    if estadia:
        id_quarto = estadia['id_quarto']
        conn.execute("UPDATE estadias SET status_estadia = 'Finalizada' WHERE id = ?", (id_estadia,))
        conn.execute("UPDATE quartos SET status = 'Disponivel' WHERE id = ?", (id_quarto,))
        conn.commit()
        flash('Check-out realizado e quarto liberado!', 'success')
    conn.close()
    return redirect(url_for('index'))

@app.route('/chave/<int:id_estadia>')
@login_required
def gerar_chave_qrcode(id_estadia):
    conn = get_db_connection()
    estadia = conn.execute('SELECT chave_digital FROM estadias WHERE id = ?', (id_estadia,)).fetchone()
    conn.close()
    if estadia and estadia['chave_digital']:
        qr_code_img = qrcode.make(estadia['chave_digital'])
        img_buffer = io.BytesIO()
        qr_code_img.save(img_buffer, 'PNG')
        img_buffer.seek(0)
        return send_file(img_buffer, mimetype='image/png')
    else:
        flash('Chave digital não encontrada para esta estadia.', 'error')
        return redirect(url_for('index'))

@app.route('/exportar_estadias')
@login_required
def exportar_estadias():
    conn = get_db_connection()
    query = """
        SELECT h.nome_completo, h.documento, q.numero, q.tipo, e.data_checkin, e.data_checkout, e.status_estadia
        FROM estadias e JOIN hospedes h ON e.id_hospede = h.id JOIN quartos q ON e.id_quarto = q.id
        ORDER BY e.data_checkin DESC
    """
    estadias_db = conn.execute(query).fetchall()
    conn.close()
    si = io.StringIO()
    cw = csv.writer(si)
    cabecalho = ['Hospede', 'Documento', 'Quarto', 'Tipo do Quarto', 'Data Check-in', 'Data Check-out', 'Status']
    cw.writerow(cabecalho)
    for estadia in estadias_db:
        cw.writerow(estadia)
    output = si.getvalue()
    return Response(output, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=relatorio_estadias.csv"})

@app.route('/hospede/excluir/<int:id_hospede>')
@login_required
def excluir_hospede(id_hospede):
    conn = get_db_connection()
    estadias = conn.execute('SELECT id FROM estadias WHERE id_hospede = ?', (id_hospede,)).fetchall()
    if len(estadias) > 0:
        flash('Não é possível excluir um hóspede que já possui estadias registradas.', 'error')
    else:
        conn.execute('DELETE FROM hospedes WHERE id = ?', (id_hospede,))
        conn.commit()
        flash('Hóspede excluído com sucesso.', 'success')
    conn.close()
    return redirect(url_for('hospedes'))

@app.route('/quarto/excluir/<int:id_quarto>')
@login_required
def excluir_quarto(id_quarto):
    conn = get_db_connection()
    estadias = conn.execute('SELECT id FROM estadias WHERE id_quarto = ?', (id_quarto,)).fetchall()
    if len(estadias) > 0:
        flash('Não é possível excluir um quarto que já foi utilizado em uma estadia.', 'error')
    else:
        conn.execute('DELETE FROM quartos WHERE id = ?', (id_quarto,))
        conn.commit()
        flash('Quarto excluído com sucesso.', 'success')
    conn.close()
    return redirect(url_for('quartos'))

@app.template_filter('strftime')
def _jinja2_filter_datetime(date_str, fmt=None):
    try:
        date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return date_obj.strftime(fmt)
    except (ValueError, TypeError):
        return date_str

if __name__ == '__main__':
    app.run(debug=True)