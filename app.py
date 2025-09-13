from flask import Flask, render_template, request, redirect
import sqlite3
import webbrowser
import threading

import os
import sqlite3

import shutil
from datetime import datetime

def fazer_backup():
    if os.path.exists('dados_empresa.db'):
        if not os.path.exists('backups'):
            os.makedirs('backups')
        agora = datetime.now().strftime('%Y-%m-%d_%H-%M')
        destino = f'backups/backup_{agora}.db'
        shutil.copy('dados_empresa.db', destino)
        print(f'Backup criado: {destino}')

def salvar_item_ordem(ordem_id, tipo, altura, comprimento, material):
    conn = sqlite3.connect('dados_empresa.db')
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO itens_ordem (ordem_id, tipo, altura, comprimento, material)
        VALUES (?, ?, ?, ?, ?)
    """, (ordem_id, tipo, altura, comprimento, material))
    conn.commit()
    conn.close()

def inicializar_banco():
    if not os.path.exists('dados_empresa.db'):
        conexao = sqlite3.connect('dados_empresa.db')
        cursor = conexao.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_produto TEXT NOT NULL,
            tipo TEXT NOT NULL,  -- persiana, cortina, toldo, papel de parede
            quantidade INTEGER NOT NULL,
            status TEXT NOT NULL,  -- instalado, manutenção, danificado, pendente, etc.
            cliente_id INTEGER,  -- pode ser NULL se ainda não estiver vinculado
            data_entrada TEXT,
            data_saida TEXT,
            observacoes TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf_cnpj TEXT NOT NULL,
            endereco TEXT,
            telefone TEXT,
            email TEXT
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ordens_servico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            data_servico TEXT,
            hora_servico TEXT,
            local_servico TEXT,
            comprimento REAL,
            altura REAL,
            materiais TEXT,
            status TEXT,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS itens_ordem (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ordem_id INTEGER,
            tipo TEXT,
            altura REAL,
            comprimento REAL,
            material TEXT,
            FOREIGN KEY (ordem_id) REFERENCES ordens_servico(id)
        )
        """)

        conexao.commit()
        cursor.close()
        conexao.close()

app = Flask(__name__)

def conectar():
    return sqlite3.connect('dados_empresa.db')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/cadastro_cliente', methods=['GET', 'POST'])
def cadastro_cliente():
    if request.method == 'POST':
        nome = request.form['nome']
        cpf_cnpj = request.form['cpf_cnpj']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']

        conexao = conectar()
        cursor = conexao.cursor()
        cursor.execute("""
            INSERT INTO clientes (nome, cpf_cnpj, endereco, telefone, email)
            VALUES (?, ?, ?, ?, ?)
        """, (nome, cpf_cnpj, endereco, telefone, email))
        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect('/clientes')

    return render_template('cadastro_cliente.html')

@app.route('/clientes', methods=['GET', 'POST'])
def listar_clientes():
    conexao = conectar()
    cursor = conexao.cursor()

    if request.method == 'POST':
        filtro = request.form['filtro']
        cursor.execute("""
            SELECT * FROM clientes
            WHERE nome LIKE ? OR cpf_cnpj LIKE ? OR email LIKE ?
        """, (f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'))
    else:
        cursor.execute("SELECT * FROM clientes")

    clientes = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template('listar_clientes.html', clientes=clientes)

@app.route('/editar_cliente/<int:id>', methods=['GET', 'POST'])
def editar_cliente(id):
    conexao = conectar()
    cursor = conexao.cursor()

    if request.method == 'POST':
        nome = request.form['nome']
        cpf_cnpj = request.form['cpf_cnpj']
        endereco = request.form['endereco']
        telefone = request.form['telefone']
        email = request.form['email']

        cursor.execute("""
            UPDATE clientes
            SET nome=?, cpf_cnpj=?, endereco=?, telefone=?, email=?
            WHERE id=?
        """, (nome, cpf_cnpj, endereco, telefone, email, id))
        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect('/clientes')

    cursor.execute("SELECT * FROM clientes WHERE id = ?", (id,))
    cliente = cursor.fetchone()
    cursor.close()
    conexao.close()
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/excluir_cliente/<int:id>')
def excluir_cliente(id):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM clientes WHERE id = ?", (id,))
    conexao.commit()
    cursor.close()
    conexao.close()
    return redirect('/clientes')

@app.route('/cadastro_os', methods=['GET', 'POST'])
def cadastro_os():
    conn = sqlite3.connect('dados_empresa.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()

    if request.method == 'POST':
        cliente_id = request.form['cliente']
        local_servico = request.form['local']
        data_servico = request.form['data']
        hora_servico = request.form['hora']
        materiais = request.form.get('observacoes')
        status = request.form['status']

        # Inserir diretamente na tabela ordens_servico
        cursor.execute("""
            INSERT INTO ordens_servico (
                cliente_id, local_servico, data_servico, hora_servico, materiais, status
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (cliente_id, local_servico, data_servico, hora_servico, materiais, status))

        ordem_id = cursor.lastrowid

        # Inserir os itens da OS
        tipos = request.form.getlist('tipo[]')
        alturas = request.form.getlist('altura[]')
        comprimentos = request.form.getlist('comprimento[]')
        materiais_item = request.form.getlist('material[]')

        for i in range(len(tipos)):
            cursor.execute("""
                INSERT INTO itens_ordem (ordem_id, tipo, altura, comprimento, material)
                VALUES (?, ?, ?, ?, ?)
            """, (ordem_id, tipos[i], alturas[i], comprimentos[i], materiais_item[i]))

        conn.commit()
        conn.close()
        return redirect('/ordens_servico')

    return render_template('cadastro_os.html', clientes=clientes)

@app.route('/ordens_servico', methods=['GET', 'POST'])
def listar_ordens():
    conexao = conectar()
    cursor = conexao.cursor()

    if request.method == 'POST':
        filtro = request.form['filtro']
        cursor.execute("""
            SELECT os.id, c.nome, os.data_servico, os.hora_servico, os.local_servico,
                   os.comprimento, os.altura, os.materiais, os.status
            FROM ordens_servico os
            JOIN clientes c ON os.cliente_id = c.id
            WHERE c.nome LIKE ? OR os.status LIKE ?
            ORDER BY os.data_servico DESC
        """, (f'%{filtro}%', f'%{filtro}%'))
    else:
        cursor.execute("""
            SELECT os.id, c.nome, os.data_servico, os.hora_servico, os.local_servico,
                   os.comprimento, os.altura, os.materiais, os.status
            FROM ordens_servico os
            JOIN clientes c ON os.cliente_id = c.id
            ORDER BY os.data_servico DESC
        """)

    ordens = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template('listar_ordens.html', ordens=ordens)

@app.route('/editar_os/<int:id>', methods=['GET', 'POST'])
def editar_os(id):
    conexao = conectar()
    cursor = conexao.cursor()

    if request.method == 'POST':
        # Dados principais da OS
        cliente_id = request.form['cliente_id']
        data_servico = request.form['data_servico']
        hora_servico = request.form['hora_servico']
        local_servico = request.form['local_servico']
        materiais = request.form['materiais']
        status = request.form['status']

        # Atualiza a OS
        cursor.execute("""
            UPDATE ordens_servico
            SET cliente_id=?, data_servico=?, hora_servico=?, local_servico=?, materiais=?, status=?
            WHERE id=?
        """, (cliente_id, data_servico, hora_servico, local_servico, materiais, status, id))

        # Itens enviados no formulário
        item_ids = request.form.getlist('item_id[]')
        tipos = request.form.getlist('tipo[]')
        alturas = request.form.getlist('altura[]')
        comprimentos = request.form.getlist('comprimento[]')
        materiais_item = request.form.getlist('material[]')

        # Buscar todos os itens existentes no banco
        cursor.execute("SELECT id FROM itens_ordem WHERE ordem_id = ?", (id,))
        itens_existentes = set(row[0] for row in cursor.fetchall())

        # Itens que vieram no formulário
        item_ids_form = set(int(i) for i in item_ids if i)

        # Descobrir quais foram removidos
        itens_removidos = itens_existentes - item_ids_form

        # Excluir os itens removidos
        for item_id in itens_removidos:
            cursor.execute("DELETE FROM itens_ordem WHERE id = ?", (item_id,))

        # Atualizar ou adicionar itens corretamente
        for item_id, tipo, altura, comprimento, material in zip(item_ids, tipos, alturas, comprimentos, materiais_item):
            if item_id:  # Atualizar item existente
                cursor.execute("""
                    UPDATE itens_ordem
                    SET tipo=?, altura=?, comprimento=?, material=?
                    WHERE id=?
                """, (tipo, altura, comprimento, material, item_id))
            else:  # Inserir novo item
                cursor.execute("""
                    INSERT INTO itens_ordem (ordem_id, tipo, altura, comprimento, material)
                    VALUES (?, ?, ?, ?, ?)
                """, (id, tipo, altura, comprimento, material))

        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect('/ordens_servico')

    # GET: carregar dados da OS e dos clientes
    cursor.execute("SELECT * FROM ordens_servico WHERE id = ?", (id,))
    ordem = cursor.fetchone()

    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()

    cursor.execute("SELECT * FROM itens_ordem WHERE ordem_id = ?", (id,))
    itens = cursor.fetchall()

    cursor.close()
    conexao.close()
    return render_template('editar_os.html', ordem=ordem, clientes=clientes, itens=itens)

@app.route('/excluir_os/<int:id>')
def excluir_os(id):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM ordens_servico WHERE id = ?", (id,))
    conexao.commit()
    cursor.close()
    conexao.close()
    return redirect('/ordens_servico')

@app.route('/ficha_os/<int:id>')
def ficha_os(id):
    conexao = conectar()
    cursor = conexao.cursor()

    # Buscar dados da OS
    cursor.execute("SELECT * FROM ordens_servico WHERE id = ?", (id,))
    ordem = cursor.fetchone()

    # Buscar cliente
    cursor.execute("SELECT nome FROM clientes WHERE id = ?", (ordem[1],))
    cliente = cursor.fetchone()[0]

    # Buscar itens da OS
    cursor.execute("SELECT * FROM itens_ordem WHERE ordem_id = ?", (id,))
    itens = cursor.fetchall()

    estimativas = []
    recomendacoes = []

    for item in itens:
        tipo = item[2]
        altura = float(item[3])
        comprimento = float(item[4])
        material = item[5]

        area = altura * comprimento

        # Recomendação de escada ou andaime
        if tipo in ['Cortina', 'Persiana'] and max(altura, comprimento) > 4:
            recomendacoes.append(f"{tipo} com {max(altura, comprimento):.2f}m: recomenda-se uso de escada ou andaime.")

        # Estimativas técnicas
        if tipo == 'Cortina':
            suportes = max(2, round(comprimento / 1.5))
            estimativas.append(f"{area:.2f} m² de tecido | {suportes} suportes")
        elif tipo == 'Persiana':
            estimativas.append(f"{area:.2f} m² de tecido")
        else:
            estimativas.append("—")

    cursor.close()
    conexao.close()

    return render_template('ficha_os.html', ordem=ordem, cliente=cliente, itens=itens, estimativas=estimativas, recomendacoes=recomendacoes)

@app.route('/cadastro_estoque', methods=['GET', 'POST'])
def cadastro_estoque():
    conexao = conectar()
    cursor = conexao.cursor()

    if request.method == 'POST':
        nome_produto = request.form['nome_produto']
        tipo = request.form['tipo']
        quantidade = request.form['quantidade']
        status = request.form['status']
        cliente_id = request.form.get('cliente_id') or None
        data_entrada = request.form['data_entrada']
        observacoes = request.form['observacoes']

        cursor.execute("""
            INSERT INTO estoque (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, observacoes))
        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect('/estoque')

    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template('cadastro_estoque.html', clientes=clientes)

@app.route('/estoque', methods=['GET', 'POST'])
def listar_estoque():
    conexao = conectar()
    cursor = conexao.cursor()

    if request.method == 'POST':
        filtro = request.form['filtro']
        cursor.execute("""
            SELECT e.id, e.nome_produto, e.tipo, e.quantidade, e.status,
                   c.nome, e.data_entrada, e.data_saida, e.observacoes
            FROM estoque e
            LEFT JOIN clientes c ON e.cliente_id = c.id
            WHERE e.nome_produto LIKE ? OR e.tipo LIKE ? OR e.status LIKE ? OR c.nome LIKE ?
            ORDER BY e.data_entrada DESC
        """, (f'%{filtro}%', f'%{filtro}%', f'%{filtro}%', f'%{filtro}%'))
    else:
        cursor.execute("""
            SELECT e.id, e.nome_produto, e.tipo, e.quantidade, e.status,
                   c.nome, e.data_entrada, e.data_saida, e.observacoes
            FROM estoque e
            LEFT JOIN clientes c ON e.cliente_id = c.id
            ORDER BY e.data_entrada DESC
        """)

    produtos = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template('listar_estoque.html', produtos=produtos)



@app.route('/editar_estoque/<int:id>', methods=['GET', 'POST'])
def editar_estoque(id):
    conexao = conectar()
    cursor = conexao.cursor()

    if request.method == 'POST':
        nome_produto = request.form['nome_produto']
        tipo = request.form['tipo']
        quantidade = request.form['quantidade']
        status = request.form['status']
        cliente_id = request.form.get('cliente_id') or None
        data_entrada = request.form['data_entrada']
        data_saida = request.form['data_saida']
        observacoes = request.form['observacoes']

        cursor.execute("""
            UPDATE estoque
            SET nome_produto=?, tipo=?, quantidade=?, status=?, cliente_id=?, data_entrada=?, data_saida=?, observacoes=?
            WHERE id=?
        """, (nome_produto, tipo, quantidade, status, cliente_id, data_entrada, data_saida, observacoes, id))
        conexao.commit()
        cursor.close()
        conexao.close()
        return redirect('/estoque')

    cursor.execute("SELECT * FROM estoque WHERE id = ?", (id,))
    produto = cursor.fetchone()
    cursor.execute("SELECT id, nome FROM clientes")
    clientes = cursor.fetchall()
    cursor.close()
    conexao.close()
    return render_template('editar_estoque.html', produto=produto, clientes=clientes)

@app.route('/excluir_estoque/<int:id>')
def excluir_estoque(id):
    conexao = conectar()
    cursor = conexao.cursor()
    cursor.execute("DELETE FROM estoque WHERE id = ?", (id,))
    conexao.commit()
    cursor.close()
    conexao.close()
    return redirect('/estoque')


def abrir_navegador():
    webbrowser.open_new("http://localhost:5000")

    from datetime import datetime

@app.context_processor
def inject_now():
    return {'now': datetime.now()}



if __name__ == '__main__':
    fazer_backup()
    inicializar_banco()
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1.5, abrir_navegador).start()
    app.run(debug=True)