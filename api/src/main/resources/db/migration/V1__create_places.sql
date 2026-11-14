CREATE TABLE places (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL CHECK (length(btrim(name)) > 0),
    geom geometry(Point, 4326) NOT NULL,
    tags text[] NOT NULL DEFAULT '{}',
    source text NOT NULL CHECK (length(btrim(source)) > 0),
    CHECK (ST_X(geom) BETWEEN -180 AND 180 AND ST_Y(geom) BETWEEN -90 AND 90)
);

CREATE INDEX places_geom_idx ON places USING gist (geom);
CREATE INDEX places_tags_idx ON places USING gin (tags);
