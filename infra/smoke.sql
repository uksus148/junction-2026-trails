-- Verify that initialization enabled both extensions and their operations work.
DO $$
BEGIN
    IF NOT ST_Contains(
        ST_MakeEnvelope(20, 49, 21, 50, 4326),
        ST_SetSRID(ST_MakePoint(20.5, 49.5), 4326)
    ) THEN
        RAISE EXCEPTION 'PostGIS failed to find the point inside the bounding box';
    END IF;

    IF ('[0,0]'::vector <-> '[3,4]'::vector) <> 5 THEN
        RAISE EXCEPTION 'pgvector returned an unexpected Euclidean distance';
    END IF;
END;
$$;
