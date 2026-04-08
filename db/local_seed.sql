INSERT INTO tasks (title, status)
VALUES
    ('Send prototype walkthrough to design', 'pending'),
    ('Prepare FlowMind investor update', 'in_progress')
ON CONFLICT DO NOTHING;

INSERT INTO calendar_events (title, start_time, end_time)
VALUES
    (
        'FlowMind demo rehearsal',
        NOW() + INTERVAL '1 day',
        NOW() + INTERVAL '1 day 45 minutes'
    ),
    (
        'Customer discovery call',
        NOW() + INTERVAL '2 days',
        NOW() + INTERVAL '2 days 30 minutes'
    )
ON CONFLICT DO NOTHING;

INSERT INTO notes (content, embedding)
SELECT
    seed.content,
    ARRAY(
        SELECT ((seed.seed + gs.i) % 97)::float8 / 97.0
        FROM generate_series(1, 768) AS gs(i)
    )::vector
FROM (
    VALUES
        (
            'Remember that Mia prefers Friday afternoon demos and wants the task summary before the call.',
            11
        ),
        (
            'The team agreed the Chaos Manager should merge tasks, calendar, and notes in one response payload.',
            23
        ),
        (
            'Prototype scope: focus on orchestration, local demo stability, and a simple task plus meeting booking flow.',
            37
        )
) AS seed(content, seed);
