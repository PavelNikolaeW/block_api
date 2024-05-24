get_blocks_query = '''
WITH RECURSIVE
    block_hierarchy AS (SELECT b.id,
                               ARRAY [b.id]             AS path,
                               0                        AS depth,
                               b.creator_id,
                               b.access_type                 AS direct_status,
                               CASE
                                   WHEN b.access_type = 'public' THEN 'public'
                                   WHEN b.access_type = 'private' THEN 'private'
                                   ELSE 'inherited' END AS effective_status,
                               b.text,
                               b."content_classList",
                               b.children_position,
                               b."classList",
                               b.layout,
                               COALESCE(b.color, 'default_color') AS color,
                               b.created_at,
                               b.updated_at,
                               b.properties,
                               true                     AS is_complete,
                               CASE
                                   WHEN b.access_type = 'inherited' AND NOT EXISTS (SELECT 1
                                                                               FROM api_block_visible_to_users bv
                                                                               WHERE bv.block_id = b.id
                                                                                 AND bv.user_id = %(user_id)s) THEN true
                                   ELSE false
                                   END                  AS is_ambiguous,
                                false AS has_children_at_max_depth
                        FROM api_block b
                        WHERE b.id = %(block_id)s
                          AND (b.access_type = 'public'
                           OR (b.access_type = 'private' AND EXISTS (SELECT 1
                                                                 FROM api_block_visible_to_users bv
                                                                 WHERE bv.block_id = b.id
                                                                   AND bv.user_id = %(user_id)s)) 
                           OR (b.access_type = 'inherited' AND EXISTS (SELECT 1
                                                                   FROM api_block_visible_to_users bv
                                                                   WHERE bv.block_id = b.id
                                                                     AND bv.user_id = %(user_id)s)))

                        UNION ALL

                        SELECT b.id,
                               bh.path || ARRAY [b.id],
                               bh.depth + 1,
                               b.creator_id,
                               b.access_type                         AS direct_status,
                               CASE
                                   WHEN b.access_type = 'public' THEN 'public'
                                   WHEN b.access_type = 'private' THEN 'private'
                                   WHEN b.access_type = 'inherited' THEN bh.effective_status
                                   ELSE bh.effective_status END AS effective_status,
                               b.text,
                               b."content_classList",
                               b.children_position,
                               b."classList",
                               b.layout,
                               COALESCE(b.color, bh.color) AS color,
                               b.created_at,
                               b.updated_at,
                               b.properties,
                               (bh.depth + 1 < 5)                   AS is_complete,
                               bh.is_ambiguous,
                               CASE
                                   WHEN bh.depth + 1 = 5 AND EXISTS (SELECT 1
                                                                     FROM api_block_children bc
                                                                     WHERE bc.from_block_id = b.id) THEN true
                                   ELSE bh.has_children_at_max_depth
                               END AS has_children_at_max_depth
                        FROM api_block b
                                 JOIN api_block_children bc ON b.id = bc.to_block_id
                                 JOIN block_hierarchy bh ON bh.id = bc.from_block_id
                        WHERE NOT b.id = ANY (bh.path)
                            AND bh.depth + 1 < 5),
    first_level_children AS (SELECT bc.from_block_id          AS parent_id,
                                    array_agg(bc.to_block_id) AS first_level_children_ids
                             FROM api_block_children bc
                             GROUP BY bc.from_block_id)
SELECT bh.id,
       string_agg(array_to_string(bh.path, ','), ';') AS paths,
       bh.creator_id,
       bh.direct_status,
       bh.effective_status,
       bh.text,
       bh."content_classList",
       bh."classList",
       bh.children_position,
       bh.layout,
       bh.color,
       bh.created_at,
       bh.updated_at,
       bh.properties,
       bool_and(bh.is_complete) AND NOT bool_or(bh.has_children_at_max_depth) AS is_fully_loaded,
       COALESCE(fl.first_level_children_ids, '{}')    AS children,
       bh.is_ambiguous
FROM block_hierarchy bh
         LEFT JOIN first_level_children fl ON bh.id = fl.parent_id
GROUP BY bh.id, bh.creator_id, bh.direct_status, bh.effective_status, bh.text, bh."content_classList", bh."classList",
         bh.layout, bh.color, bh.created_at, bh.updated_at, fl.first_level_children_ids, bh.children_position, bh.properties,
         bh.is_ambiguous
ORDER BY bh.id;
'''