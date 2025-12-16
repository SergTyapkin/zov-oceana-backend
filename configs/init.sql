------- Users data -------
CREATE TABLE IF NOT EXISTS users (
    id               SERIAL PRIMARY KEY,
    tgUsername       TEXT DEFAULT NULL UNIQUE,
    tgId             TEXT DEFAULT NULL UNIQUE,
    email            TEXT DEFAULT NULL UNIQUE,
    isConfirmedEmail BOOLEAN NOT NULL DEFAULT FALSE,
    tel              TEXT DEFAULT NULL UNIQUE,
    avatarUrl        TEXT DEFAULT NULL,
    familyName       TEXT DEFAULT NULL,
    givenName        TEXT DEFAULT NULL,
    middleName       TEXT DEFAULT NULL,
    joinedDate       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    password         TEXT NOT NULL,
    partnerStatus    BOOLEAN DEFAULT FALSE,
    referrerId       INT REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    partnerBonuses   FLOAT NOT NULL DEFAULT 0,

    isEmailNotificationsOn  BOOLEAN DEFAULT TRUE,

    canEditOrders           BOOLEAN DEFAULT FALSE,
    canEditUsers            BOOLEAN DEFAULT FALSE,
    canEditGoods            BOOLEAN DEFAULT FALSE,
    canEditPartners         BOOLEAN DEFAULT FALSE,
    canExecuteSQL           BOOLEAN DEFAULT FALSE,
    canEditHistory          BOOLEAN DEFAULT FALSE,
    canEditGlobals          BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS sessions (
    userId   SERIAL NOT NULL REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    token    TEXT NOT NULL UNIQUE,
    expires  TIMESTAMP WITH TIME ZONE,
    ip          TEXT,
    browser     TEXT,
    os          TEXT,
    geolocation TEXT
);

CREATE TABLE IF NOT EXISTS secretCodes (
    id             SERIAL PRIMARY KEY,
    userId         TEXT NOT NULL,
    code           TEXT NOT NULL UNIQUE,
    type           TEXT NOT NULL,
    meta           TEXT DEFAULT NULL,
    expires        TIMESTAMP WITH TIME ZONE NOT NULL,
    UNIQUE (userId, type)
);

------ Images ------
CREATE TABLE IF NOT EXISTS images (
    id           SERIAL PRIMARY KEY,
    type         TEXT NOT NULL,
    path         TEXT,
    bytes        BYTEA
);

------ Addresses data ------
CREATE TABLE IF NOT EXISTS addresses (
    id             SERIAL PRIMARY KEY,
    userId         INT REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    createdDate    TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    title          TEXT DEFAULT NULL,
    city           TEXT DEFAULT NULL,
    street         TEXT DEFAULT NULL,
    house          TEXT DEFAULT NULL,
    entrance       TEXT DEFAULT NULL,
    apartment          TEXT DEFAULT NULL,
    floor          TEXT DEFAULT NULL,
    code           TEXT DEFAULT NULL,
    comment        TEXT DEFAULT NULL
);

------ Goods data -------
CREATE TABLE IF NOT EXISTS goods (
    id                   SERIAL PRIMARY KEY,
    title                TEXT NOT NULL DEFAULT '',
    description          TEXT DEFAULT NULL,
    createdDate          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    fromLocation         TEXT DEFAULT NULL,
    amountLeft           FLOAT NOT NULL,
    amountStep           FLOAT NOT NULL DEFAULT 1,
    amountMin            FLOAT NOT NULL DEFAULT 0,
    cost                 FLOAT NOT NULL,
    isWeighed            BOOLEAN NOT NULL,
    isOnSale             BOOLEAN NOT NULL,
    characters           TEXT
);

CREATE TABLE IF NOT EXISTS categories (
    id                   SERIAL PRIMARY KEY,
    title                TEXT NOT NULL DEFAULT '',
    description          TEXT DEFAULT NULL,
    imageId              INT REFERENCES images(id) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS goodsCategories (
    id           SERIAL PRIMARY KEY,
    goodsId      INT NOT NULL REFERENCES goods(id) ON DELETE CASCADE ON UPDATE CASCADE,
    categoryId   INT NOT NULL REFERENCES categories(id) ON DELETE CASCADE ON UPDATE CASCADE,
    UNIQUE (goodsId, categoryId)
);

CREATE TABLE IF NOT EXISTS goodsImages (
    id           SERIAL PRIMARY KEY,
    goodsId      INT NOT NULL REFERENCES goods(id) ON DELETE CASCADE ON UPDATE CASCADE,
    imageId      INT NOT NULL REFERENCES images(id) ON DELETE CASCADE ON UPDATE CASCADE,
    sortingKey   INT NOT NULL,
    UNIQUE (goodsId, sortingKey),
    UNIQUE (goodsId, imageId)
);


------ Orders data ------
do $$ begin
    if not exists (select 1 from pg_type where typname = 'orderstatus') then
        CREATE TYPE orderStatus AS ENUM ('created', 'paid', 'prepared', 'delivered', 'cancelled');
    end if;
end $$;

CREATE TABLE IF NOT EXISTS orders (
    id              SERIAL PRIMARY KEY,
    number          INT NOT NULL UNIQUE,
    secretCode      TEXT NOT NULL,
    userId          INT REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    addressId       INT REFERENCES addresses(id) ON DELETE SET NULL ON UPDATE CASCADE,
    addressTextCopy TEXT NOT NULL,
    commentTextCopy TEXT NOT NULL,
    createdDate     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updatedDate     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status          orderStatus NOT NULL DEFAULT 'created',
    trackingCode    TEXT DEFAULT NULL
);
CREATE TABLE IF NOT EXISTS ordersGoods (
    id              SERIAL PRIMARY KEY,
    orderId         INT REFERENCES orders(id) ON DELETE CASCADE ON UPDATE CASCADE,
    goodsId         INT REFERENCES goods(id) ON DELETE SET NULL ON UPDATE CASCADE,
    cost            FLOAT NOT NULL,
    amount          FLOAT NOT NULL,
    UNIQUE (goodsId, orderId)
);

------- Carts data -------
CREATE TABLE IF NOT EXISTS goodsInCarts (
    id             SERIAL PRIMARY KEY,
    goodsId        INT NOT NULL REFERENCES goods(id) ON DELETE CASCADE ON UPDATE CASCADE,
    userId         INT NOT NULL REFERENCES users(id) ON DELETE CASCADE ON UPDATE CASCADE,
    addedDate      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    amount         FLOAT NOT NULL,
    UNIQUE (goodsId, userId)
);


------ Partner bonuses history ------
CREATE TABLE IF NOT EXISTS partnerBonusesHistory (
    id             SERIAL PRIMARY KEY,
    userId         INT REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE NOT NULL,
    fromUserId     INT REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    value          FLOAT NOT NULL,
    orderId        INT REFERENCES orders(id) ON DELETE SET NULL ON UPDATE CASCADE DEFAULT NULL,
    date           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    comment        TEXT
);

------ Total history ------
CREATE TABLE IF NOT EXISTS history (
    id             SERIAL PRIMARY KEY,
    userId         INT REFERENCES users(id) ON DELETE SET NULL ON UPDATE CASCADE,
    type           TEXT NOT NULL,
    text           TEXT NOT NULL,
    date           TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

------ Globals ------
CREATE TABLE IF NOT EXISTS globals (
    isOnMaintenance   BOOLEAN NOT NULL DEFAULT FALSE,
    goodsIdsOnLanding INT[] NOT NULL DEFAULT ARRAY[]::INT[]
);
