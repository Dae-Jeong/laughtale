\set ON_ERROR_STOP on
\getenv writer_password CHAT_WRITER_PASSWORD
\getenv reader_password CHAT_READER_PASSWORD
\getenv replication_password REPLICATION_PASSWORD

CREATE ROLE chat_owner NOLOGIN;
CREATE ROLE chat_writer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'writer_password';
CREATE ROLE chat_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD :'reader_password';
CREATE ROLE chat_replicator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE REPLICATION PASSWORD :'replication_password';
ALTER DATABASE laughtale_chat OWNER TO chat_owner;
REVOKE ALL ON DATABASE laughtale_chat FROM PUBLIC;
GRANT CONNECT ON DATABASE laughtale_chat TO chat_writer, chat_reader;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

SET ROLE chat_owner;
CREATE SCHEMA chat AUTHORIZATION chat_owner;
GRANT USAGE ON SCHEMA chat TO chat_writer, chat_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA chat GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO chat_writer;
ALTER DEFAULT PRIVILEGES IN SCHEMA chat GRANT SELECT ON TABLES TO chat_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA chat GRANT USAGE, SELECT ON SEQUENCES TO chat_writer;
RESET ROLE;
ALTER ROLE chat_writer IN DATABASE laughtale_chat SET search_path = chat, pg_catalog;
ALTER ROLE chat_reader IN DATABASE laughtale_chat SET search_path = chat, pg_catalog;
SELECT pg_create_physical_replication_slot('chat_replica');
