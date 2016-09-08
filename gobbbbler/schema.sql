create table users (
    users_id        serial primary key,
    name            text not null,
    email           text not null,
    password_hash   varchar(32),
    is_active       boolean not null default true
);

create unique index users_name on users ( name );
create unique index users_email on users ( email );

create table posts (
    posts_id    serial primary key,
    users_id    int not null references users,
    post        text not null,
    post_date   timestamp with time zone not null default now()
);

create index posts_user on posts ( users_id );
create index posts_date on posts ( post_date );
