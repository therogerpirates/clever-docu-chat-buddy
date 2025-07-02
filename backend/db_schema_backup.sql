--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


--
-- Name: filestatus; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.filestatus AS ENUM (
    'PROCESSING',
    'READY',
    'ERROR'
);


--
-- Name: filetype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.filetype AS ENUM (
    'CSV',
    'XLSX',
    'PDF',
    'WEBSITE'
);


--
-- Name: ragtype; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.ragtype AS ENUM (
    'SQL',
    'SEMANTIC'
);


--
-- Name: userrole; Type: TYPE; Schema: public; Owner: -
--

CREATE TYPE public.userrole AS ENUM (
    'ADMIN',
    'MANAGER',
    'EMPLOYEE'
);


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: csv_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.csv_chunks (
    id integer NOT NULL,
    document_id integer,
    row_number integer NOT NULL,
    content text NOT NULL,
    embedding json NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: csv_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.csv_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: csv_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.csv_chunks_id_seq OWNED BY public.csv_chunks.id;


--
-- Name: csv_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.csv_documents (
    id integer NOT NULL,
    file_id integer,
    row_count integer NOT NULL,
    column_count integer NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    header jsonb
);


--
-- Name: csv_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.csv_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: csv_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.csv_documents_id_seq OWNED BY public.csv_documents.id;


--
-- Name: file_restrictions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.file_restrictions (
    file_id integer,
    user_id integer
);


--
-- Name: files; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.files (
    id integer NOT NULL,
    file_uuid uuid,
    filename character varying NOT NULL,
    original_filename character varying NOT NULL,
    file_path character varying NOT NULL,
    rag_type public.ragtype,
    description character varying,
    status public.filestatus NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    uploaded_by_id integer NOT NULL,
    file_type public.filetype,
    file_size bigint,
    file_metadata jsonb,
    page_count integer,
    chunk_count integer,
    is_processed boolean DEFAULT false,
    processing_error text
);


--
-- Name: files_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.files_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: files_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.files_id_seq OWNED BY public.files.id;


--
-- Name: pdf_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pdf_chunks (
    id integer NOT NULL,
    document_id integer,
    page_number integer NOT NULL,
    content text NOT NULL,
    embedding json NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: pdf_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pdf_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pdf_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pdf_chunks_id_seq OWNED BY public.pdf_chunks.id;


--
-- Name: pdf_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pdf_documents (
    id integer NOT NULL,
    file_id integer,
    title character varying,
    author character varying,
    page_count integer,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    document_metadata jsonb
);


--
-- Name: pdf_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pdf_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pdf_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pdf_documents_id_seq OWNED BY public.pdf_documents.id;


--
-- Name: processed_data; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.processed_data (
    id integer NOT NULL,
    file_id integer,
    content json NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: processed_data_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.processed_data_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: processed_data_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.processed_data_id_seq OWNED BY public.processed_data.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    username character varying NOT NULL,
    email character varying NOT NULL,
    password_hash character varying NOT NULL,
    role public.userrole NOT NULL,
    is_active boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: website_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.website_chunks (
    id integer NOT NULL,
    document_id integer,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    embedding json NOT NULL,
    chunk_metadata json,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: website_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.website_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: website_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.website_chunks_id_seq OWNED BY public.website_chunks.id;


--
-- Name: website_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.website_documents (
    id integer NOT NULL,
    file_id integer NOT NULL,
    url text NOT NULL,
    title text,
    description text,
    domain text,
    status text NOT NULL,
    error_message text,
    document_metadata json,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    uploaded_by_id integer,
    rag_type character varying(50) DEFAULT 'SEMANTIC'::character varying
);


--
-- Name: website_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.website_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: website_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.website_documents_id_seq OWNED BY public.website_documents.id;


--
-- Name: xlsx_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.xlsx_chunks (
    id integer NOT NULL,
    document_id integer,
    sheet_name character varying NOT NULL,
    row_number integer NOT NULL,
    content text NOT NULL,
    embedding json NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone
);


--
-- Name: xlsx_chunks_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.xlsx_chunks_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: xlsx_chunks_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.xlsx_chunks_id_seq OWNED BY public.xlsx_chunks.id;


--
-- Name: xlsx_documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.xlsx_documents (
    id integer NOT NULL,
    file_id integer,
    sheet_count integer NOT NULL,
    row_count integer NOT NULL,
    column_count integer NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    sheet_names jsonb
);


--
-- Name: xlsx_documents_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.xlsx_documents_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: xlsx_documents_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.xlsx_documents_id_seq OWNED BY public.xlsx_documents.id;


--
-- Name: csv_chunks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.csv_chunks ALTER COLUMN id SET DEFAULT nextval('public.csv_chunks_id_seq'::regclass);


--
-- Name: csv_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.csv_documents ALTER COLUMN id SET DEFAULT nextval('public.csv_documents_id_seq'::regclass);


--
-- Name: files id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files ALTER COLUMN id SET DEFAULT nextval('public.files_id_seq'::regclass);


--
-- Name: pdf_chunks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_chunks ALTER COLUMN id SET DEFAULT nextval('public.pdf_chunks_id_seq'::regclass);


--
-- Name: pdf_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_documents ALTER COLUMN id SET DEFAULT nextval('public.pdf_documents_id_seq'::regclass);


--
-- Name: processed_data id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_data ALTER COLUMN id SET DEFAULT nextval('public.processed_data_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: website_chunks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.website_chunks ALTER COLUMN id SET DEFAULT nextval('public.website_chunks_id_seq'::regclass);


--
-- Name: website_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.website_documents ALTER COLUMN id SET DEFAULT nextval('public.website_documents_id_seq'::regclass);


--
-- Name: xlsx_chunks id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xlsx_chunks ALTER COLUMN id SET DEFAULT nextval('public.xlsx_chunks_id_seq'::regclass);


--
-- Name: xlsx_documents id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xlsx_documents ALTER COLUMN id SET DEFAULT nextval('public.xlsx_documents_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: csv_chunks csv_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.csv_chunks
    ADD CONSTRAINT csv_chunks_pkey PRIMARY KEY (id);


--
-- Name: csv_documents csv_documents_file_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.csv_documents
    ADD CONSTRAINT csv_documents_file_id_key UNIQUE (file_id);


--
-- Name: csv_documents csv_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.csv_documents
    ADD CONSTRAINT csv_documents_pkey PRIMARY KEY (id);


--
-- Name: files files_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_pkey PRIMARY KEY (id);


--
-- Name: pdf_chunks pdf_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_chunks
    ADD CONSTRAINT pdf_chunks_pkey PRIMARY KEY (id);


--
-- Name: pdf_documents pdf_documents_file_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_documents
    ADD CONSTRAINT pdf_documents_file_id_key UNIQUE (file_id);


--
-- Name: pdf_documents pdf_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_documents
    ADD CONSTRAINT pdf_documents_pkey PRIMARY KEY (id);


--
-- Name: processed_data processed_data_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_data
    ADD CONSTRAINT processed_data_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: website_chunks website_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.website_chunks
    ADD CONSTRAINT website_chunks_pkey PRIMARY KEY (id);


--
-- Name: website_documents website_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.website_documents
    ADD CONSTRAINT website_documents_pkey PRIMARY KEY (id);


--
-- Name: xlsx_chunks xlsx_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xlsx_chunks
    ADD CONSTRAINT xlsx_chunks_pkey PRIMARY KEY (id);


--
-- Name: xlsx_documents xlsx_documents_file_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xlsx_documents
    ADD CONSTRAINT xlsx_documents_file_id_key UNIQUE (file_id);


--
-- Name: xlsx_documents xlsx_documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xlsx_documents
    ADD CONSTRAINT xlsx_documents_pkey PRIMARY KEY (id);


--
-- Name: ix_csv_chunks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_csv_chunks_id ON public.csv_chunks USING btree (id);


--
-- Name: ix_csv_documents_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_csv_documents_id ON public.csv_documents USING btree (id);


--
-- Name: ix_files_file_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_files_file_uuid ON public.files USING btree (file_uuid);


--
-- Name: ix_files_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_files_id ON public.files USING btree (id);


--
-- Name: ix_pdf_chunks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pdf_chunks_id ON public.pdf_chunks USING btree (id);


--
-- Name: ix_pdf_documents_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_pdf_documents_id ON public.pdf_documents USING btree (id);


--
-- Name: ix_processed_data_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_processed_data_id ON public.processed_data USING btree (id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_id ON public.users USING btree (id);


--
-- Name: ix_users_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_users_username ON public.users USING btree (username);


--
-- Name: ix_website_chunks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_website_chunks_id ON public.website_chunks USING btree (id);


--
-- Name: ix_xlsx_chunks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_xlsx_chunks_id ON public.xlsx_chunks USING btree (id);


--
-- Name: ix_xlsx_documents_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_xlsx_documents_id ON public.xlsx_documents USING btree (id);


--
-- Name: csv_chunks csv_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.csv_chunks
    ADD CONSTRAINT csv_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.csv_documents(id) ON DELETE CASCADE;


--
-- Name: csv_documents csv_documents_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.csv_documents
    ADD CONSTRAINT csv_documents_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.files(id) ON DELETE CASCADE;


--
-- Name: file_restrictions file_restrictions_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_restrictions
    ADD CONSTRAINT file_restrictions_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.files(id) ON DELETE CASCADE;


--
-- Name: file_restrictions file_restrictions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.file_restrictions
    ADD CONSTRAINT file_restrictions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: files files_uploaded_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.files
    ADD CONSTRAINT files_uploaded_by_id_fkey FOREIGN KEY (uploaded_by_id) REFERENCES public.users(id);


--
-- Name: pdf_chunks pdf_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_chunks
    ADD CONSTRAINT pdf_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.pdf_documents(id) ON DELETE CASCADE;


--
-- Name: pdf_documents pdf_documents_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pdf_documents
    ADD CONSTRAINT pdf_documents_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.files(id) ON DELETE CASCADE;


--
-- Name: processed_data processed_data_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.processed_data
    ADD CONSTRAINT processed_data_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.files(id) ON DELETE CASCADE;


--
-- Name: website_chunks website_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.website_chunks
    ADD CONSTRAINT website_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.website_documents(id) ON DELETE CASCADE;


--
-- Name: xlsx_chunks xlsx_chunks_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xlsx_chunks
    ADD CONSTRAINT xlsx_chunks_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.xlsx_documents(id) ON DELETE CASCADE;


--
-- Name: xlsx_documents xlsx_documents_file_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.xlsx_documents
    ADD CONSTRAINT xlsx_documents_file_id_fkey FOREIGN KEY (file_id) REFERENCES public.files(id) ON DELETE CASCADE;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;


--
-- PostgreSQL database dump complete
--

