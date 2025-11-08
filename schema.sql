DROP TABLE IF EXISTS estadias;
DROP TABLE IF EXISTS hospedes;
DROP TABLE IF EXISTS quartos;

CREATE TABLE quartos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero INTEGER UNIQUE NOT NULL,
    tipo TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Disponivel'
);

CREATE TABLE hospedes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo TEXT NOT NULL,
    documento TEXT UNIQUE NOT NULL
);

CREATE TABLE estadias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_hospede INTEGER NOT NULL,
    id_quarto INTEGER NOT NULL,
    data_checkin TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_checkout DATE,
    chave_digital TEXT,
    status_estadia TEXT NOT NULL DEFAULT 'Ativa',
    FOREIGN KEY (id_hospede) REFERENCES hospedes (id),
    FOREIGN KEY (id_quarto) REFERENCES quartos (id)
);