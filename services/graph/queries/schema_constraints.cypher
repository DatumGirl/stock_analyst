// Uniqueness constraints and lookup indexes.
// Applied by graph_service.migrations.apply_schema; safe to re-run.
CREATE CONSTRAINT ON (n:Company) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:Sector) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:Industry) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:ETF) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:Country) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:Commodity) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:Technology) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:Theme) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:RiskFactor) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:NewsEvent) ASSERT n.key IS UNIQUE;
CREATE CONSTRAINT ON (n:MacroEvent) ASSERT n.key IS UNIQUE;
CREATE INDEX ON :Company(key);
CREATE INDEX ON :Theme(key);
CREATE INDEX ON :NewsEvent(as_of);
CREATE INDEX ON :MacroEvent(as_of);
