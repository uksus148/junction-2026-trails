CREATE TABLE routes (
    id uuid PRIMARY KEY,
    geom geometry(LineString, 4326) NOT NULL,
    start_geom geometry(Point, 4326) NOT NULL,
    end_geom geometry(Point, 4326) NOT NULL,
    distance_km double precision NOT NULL CHECK (distance_km >= 0 AND distance_km < 'Infinity'::float8),
    ascent_m double precision NOT NULL CHECK (ascent_m >= 0 AND ascent_m < 'Infinity'::float8),
    duration_min double precision NOT NULL CHECK (duration_min >= 0 AND duration_min < 'Infinity'::float8),
    preferences text[] NOT NULL,
    CHECK (ST_NPoints(geom) >= 2)
);

CREATE INDEX routes_geom_idx ON routes USING gist (geom);

CREATE TABLE route_places (
    route_id uuid NOT NULL REFERENCES routes(id) ON DELETE CASCADE,
    position integer NOT NULL CHECK (position >= 0),
    place_id uuid NOT NULL REFERENCES places(id),
    PRIMARY KEY (route_id, position)
);

CREATE INDEX route_places_place_idx ON route_places (place_id);
