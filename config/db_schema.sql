--
-- PostgreSQL database dump
--

-- Dumped from database version 9.4beta2
-- Dumped by pg_dump version 9.4beta2
-- Started on 2014-12-03 16:56:37 EST

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 2095 (class 1262 OID 16388)
-- Name: robotgame; Type: DATABASE; Schema: -; Owner: robot
--

CREATE DATABASE robotgame WITH TEMPLATE = template0 ENCODING = 'UTF8' LC_COLLATE = 'en_EN.UTF-8' LC_CTYPE = 'en_EN.UTF-8';


ALTER DATABASE robotgame OWNER TO robot;

\connect robotgame

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 184 (class 3079 OID 11861)
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- TOC entry 2097 (class 0 OID 0)
-- Dependencies: 184
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- TOC entry 172 (class 1259 OID 16418)
-- Name: fail_bots; Type: TABLE; Schema: public; Owner: robot; Tablespace: 
--

CREATE TABLE fail_bots (
    id integer NOT NULL,
    hash character(32) NOT NULL,
    code text NOT NULL
);


ALTER TABLE fail_bots OWNER TO robot;

--
-- TOC entry 173 (class 1259 OID 16424)
-- Name: fail_bots_id_seq; Type: SEQUENCE; Schema: public; Owner: robot
--

CREATE SEQUENCE fail_bots_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE fail_bots_id_seq OWNER TO robot;

--
-- TOC entry 2098 (class 0 OID 0)
-- Dependencies: 173
-- Name: fail_bots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: robot
--

ALTER SEQUENCE fail_bots_id_seq OWNED BY fail_bots.id;


--
-- TOC entry 174 (class 1259 OID 16426)
-- Name: history; Type: TABLE; Schema: public; Owner: robot; Tablespace: 
--

CREATE TABLE history (
    id integer NOT NULL,
    match_id integer NOT NULL,
    data text,
    "timestamp" integer NOT NULL
);


ALTER TABLE history OWNER TO robot;

--
-- TOC entry 175 (class 1259 OID 16432)
-- Name: history_id_seq; Type: SEQUENCE; Schema: public; Owner: robot
--

CREATE SEQUENCE history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE history_id_seq OWNER TO robot;

--
-- TOC entry 2099 (class 0 OID 0)
-- Dependencies: 175
-- Name: history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: robot
--

ALTER SEQUENCE history_id_seq OWNED BY history.id;


--
-- TOC entry 176 (class 1259 OID 16434)
-- Name: matches; Type: TABLE; Schema: public; Owner: robot; Tablespace: 
--

CREATE TABLE matches (
    id integer NOT NULL,
    r1_id integer,
    r2_id integer,
    winner integer,
    "timestamp" integer DEFAULT date_part('epoch'::text, now()),
    ranked boolean DEFAULT false,
    state smallint DEFAULT 0,
    r1_score integer,
    r2_score integer,
    r1_rating double precision,
    r2_rating double precision,
    seed integer DEFAULT 0,
    r1_ranking integer,
    r2_ranking integer,
    k_factor integer DEFAULT 32,
    r1_time double precision,
    r2_time double precision
);


ALTER TABLE matches OWNER TO robot;

--
-- TOC entry 177 (class 1259 OID 16442)
-- Name: matches_id_seq; Type: SEQUENCE; Schema: public; Owner: robot
--

CREATE SEQUENCE matches_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE matches_id_seq OWNER TO robot;

--
-- TOC entry 2100 (class 0 OID 0)
-- Dependencies: 177
-- Name: matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: robot
--

ALTER SEQUENCE matches_id_seq OWNED BY matches.id;


--
-- TOC entry 178 (class 1259 OID 16444)
-- Name: os_bots; Type: TABLE; Schema: public; Owner: robot; Tablespace: 
--

CREATE TABLE os_bots (
    id integer NOT NULL,
    hash character(32) NOT NULL,
    code text NOT NULL
);


ALTER TABLE os_bots OWNER TO robot;

--
-- TOC entry 179 (class 1259 OID 16450)
-- Name: os_bots_id_seq; Type: SEQUENCE; Schema: public; Owner: robot
--

CREATE SEQUENCE os_bots_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE os_bots_id_seq OWNER TO robot;

--
-- TOC entry 2101 (class 0 OID 0)
-- Dependencies: 179
-- Name: os_bots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: robot
--

ALTER SEQUENCE os_bots_id_seq OWNED BY os_bots.id;


--
-- TOC entry 180 (class 1259 OID 16452)
-- Name: robots; Type: TABLE; Schema: public; Owner: robot; Tablespace: 
--

CREATE TABLE robots (
    id integer NOT NULL,
    user_id integer,
    code text DEFAULT ''::text,
    rating double precision,
    name text,
    saved boolean DEFAULT false,
    compiled_code text DEFAULT ''::text,
    passed boolean DEFAULT false,
    changed_since_sbtest boolean DEFAULT true,
    compiled boolean DEFAULT false,
    open_source boolean DEFAULT false,
    disabled boolean DEFAULT false,
    automatch boolean DEFAULT true,
    last_updated integer DEFAULT date_part('epoch'::text, now()),
    last_opponent integer,
    deleted boolean DEFAULT false,
    last_rating double precision DEFAULT 1200 NOT NULL,
    priority double precision DEFAULT 1.0 NOT NULL,
    last_match integer,
    "time" double precision DEFAULT 0 NOT NULL,
    fast boolean,
    short boolean,
    winrate double precision DEFAULT 1.0
);


ALTER TABLE robots OWNER TO robot;

--
-- TOC entry 181 (class 1259 OID 16473)
-- Name: robots_id_seq; Type: SEQUENCE; Schema: public; Owner: robot
--

CREATE SEQUENCE robots_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE robots_id_seq OWNER TO robot;

--
-- TOC entry 2102 (class 0 OID 0)
-- Dependencies: 181
-- Name: robots_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: robot
--

ALTER SEQUENCE robots_id_seq OWNED BY robots.id;


--
-- TOC entry 182 (class 1259 OID 16475)
-- Name: users; Type: TABLE; Schema: public; Owner: robot; Tablespace: 
--

CREATE TABLE users (
    id integer NOT NULL,
    username character varying(40) NOT NULL,
    pw_hash character varying(40) NOT NULL,
    pw_salt text,
    about text DEFAULT ''::text,
    challenges integer DEFAULT 0,
    vip boolean DEFAULT false,
    account_type smallint DEFAULT 0,
    registered_on integer DEFAULT date_part('epoch'::text, now()),
    last_active integer DEFAULT 0,
    extra_bots integer DEFAULT 0
);


ALTER TABLE users OWNER TO robot;

--
-- TOC entry 183 (class 1259 OID 16488)
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: robot
--

CREATE SEQUENCE users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE users_id_seq OWNER TO robot;

--
-- TOC entry 2103 (class 0 OID 0)
-- Dependencies: 183
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: robot
--

ALTER SEQUENCE users_id_seq OWNED BY users.id;


--
-- TOC entry 1920 (class 2604 OID 16490)
-- Name: id; Type: DEFAULT; Schema: public; Owner: robot
--

ALTER TABLE ONLY fail_bots ALTER COLUMN id SET DEFAULT nextval('fail_bots_id_seq'::regclass);


--
-- TOC entry 1921 (class 2604 OID 16491)
-- Name: id; Type: DEFAULT; Schema: public; Owner: robot
--

ALTER TABLE ONLY history ALTER COLUMN id SET DEFAULT nextval('history_id_seq'::regclass);


--
-- TOC entry 1927 (class 2604 OID 16492)
-- Name: id; Type: DEFAULT; Schema: public; Owner: robot
--

ALTER TABLE ONLY matches ALTER COLUMN id SET DEFAULT nextval('matches_id_seq'::regclass);


--
-- TOC entry 1928 (class 2604 OID 16493)
-- Name: id; Type: DEFAULT; Schema: public; Owner: robot
--

ALTER TABLE ONLY os_bots ALTER COLUMN id SET DEFAULT nextval('os_bots_id_seq'::regclass);


--
-- TOC entry 1944 (class 2604 OID 16494)
-- Name: id; Type: DEFAULT; Schema: public; Owner: robot
--

ALTER TABLE ONLY robots ALTER COLUMN id SET DEFAULT nextval('robots_id_seq'::regclass);


--
-- TOC entry 1952 (class 2604 OID 16495)
-- Name: id; Type: DEFAULT; Schema: public; Owner: robot
--

ALTER TABLE ONLY users ALTER COLUMN id SET DEFAULT nextval('users_id_seq'::regclass);


--
-- TOC entry 1954 (class 2606 OID 16497)
-- Name: fail_bots_hash_key; Type: CONSTRAINT; Schema: public; Owner: robot; Tablespace: 
--

ALTER TABLE ONLY fail_bots
    ADD CONSTRAINT fail_bots_hash_key UNIQUE (hash);


--
-- TOC entry 1956 (class 2606 OID 16499)
-- Name: fail_bots_pkey; Type: CONSTRAINT; Schema: public; Owner: robot; Tablespace: 
--

ALTER TABLE ONLY fail_bots
    ADD CONSTRAINT fail_bots_pkey PRIMARY KEY (id);


--
-- TOC entry 1958 (class 2606 OID 16501)
-- Name: history_pkey; Type: CONSTRAINT; Schema: public; Owner: robot; Tablespace: 
--

ALTER TABLE ONLY history
    ADD CONSTRAINT history_pkey PRIMARY KEY (id);


--
-- TOC entry 1963 (class 2606 OID 16503)
-- Name: matches_pkey; Type: CONSTRAINT; Schema: public; Owner: robot; Tablespace: 
--

ALTER TABLE ONLY matches
    ADD CONSTRAINT matches_pkey PRIMARY KEY (id);


--
-- TOC entry 1968 (class 2606 OID 16505)
-- Name: os_bots_hash_key; Type: CONSTRAINT; Schema: public; Owner: robot; Tablespace: 
--

ALTER TABLE ONLY os_bots
    ADD CONSTRAINT os_bots_hash_key UNIQUE (hash);


--
-- TOC entry 1970 (class 2606 OID 16507)
-- Name: os_bots_pkey; Type: CONSTRAINT; Schema: public; Owner: robot; Tablespace: 
--

ALTER TABLE ONLY os_bots
    ADD CONSTRAINT os_bots_pkey PRIMARY KEY (id);


--
-- TOC entry 1974 (class 2606 OID 16509)
-- Name: robots_pkey; Type: CONSTRAINT; Schema: public; Owner: robot; Tablespace: 
--

ALTER TABLE ONLY robots
    ADD CONSTRAINT robots_pkey PRIMARY KEY (id);


--
-- TOC entry 1977 (class 2606 OID 16511)
-- Name: users_pkey; Type: CONSTRAINT; Schema: public; Owner: robot; Tablespace: 
--

ALTER TABLE ONLY users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 1959 (class 1259 OID 16512)
-- Name: history_timestamp_idx; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX history_timestamp_idx ON history USING btree ("timestamp");


--
-- TOC entry 1960 (class 1259 OID 16513)
-- Name: match_id; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX match_id ON history USING btree (match_id);


--
-- TOC entry 1961 (class 1259 OID 16514)
-- Name: matches_id_idx; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX matches_id_idx ON matches USING btree (id) WHERE ((state = 0) OR (state = 1));


--
-- TOC entry 1964 (class 1259 OID 16515)
-- Name: matches_timestamp; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX matches_timestamp ON matches USING btree ("timestamp");


--
-- TOC entry 1965 (class 1259 OID 16516)
-- Name: r1_id; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX r1_id ON matches USING btree (r1_id);


--
-- TOC entry 1966 (class 1259 OID 16517)
-- Name: r2_id; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX r2_id ON matches USING btree (r2_id);


--
-- TOC entry 1971 (class 1259 OID 16518)
-- Name: rating; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX rating ON robots USING btree (rating);


--
-- TOC entry 1972 (class 1259 OID 16519)
-- Name: robots_id_idx; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX robots_id_idx ON robots USING btree (id) WHERE (fast OR short);


--
-- TOC entry 1975 (class 1259 OID 16520)
-- Name: user_id; Type: INDEX; Schema: public; Owner: robot; Tablespace: 
--

CREATE INDEX user_id ON robots USING btree (user_id);


--
-- TOC entry 1978 (class 2606 OID 16521)
-- Name: history_match_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: robot
--

ALTER TABLE ONLY history
    ADD CONSTRAINT history_match_id_fkey FOREIGN KEY (match_id) REFERENCES matches(id);


--
-- TOC entry 1979 (class 2606 OID 16526)
-- Name: matches_r1_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: robot
--

ALTER TABLE ONLY matches
    ADD CONSTRAINT matches_r1_id_fkey FOREIGN KEY (r1_id) REFERENCES robots(id);


--
-- TOC entry 1980 (class 2606 OID 16531)
-- Name: matches_r2_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: robot
--

ALTER TABLE ONLY matches
    ADD CONSTRAINT matches_r2_id_fkey FOREIGN KEY (r2_id) REFERENCES robots(id);


--
-- TOC entry 1981 (class 2606 OID 16536)
-- Name: robots_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: robot
--

ALTER TABLE ONLY robots
    ADD CONSTRAINT robots_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE CASCADE ON DELETE CASCADE;


-- Completed on 2014-12-03 16:56:37 EST

--
-- PostgreSQL database dump complete
--

