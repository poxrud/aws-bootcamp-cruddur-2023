-- this file was manually created
INSERT INTO
  public.users (display_name, email, handle, cognito_user_id)
VALUES
  (
    'Phil Oxrud',
    'philoxrud@gmail.com',
    'philoxrud',
    'MOCK'
  ),
  (
    'Alt Phil',
    'philoxrud+alt@gmail.com',
    'altphil',
    'MOCK'
  ),
  (
    'John Smith',
    'philoxrud+johnsmith@gmail.com',
    'johnsmith',
    'MOCK'
  ),
  (
    'Lando Mollari',
    'philoxrud+lando@gmail.com',
    'landomollari',
    'MOCK'
  );
INSERT INTO
  public.activities (user_uuid, message, expires_at)
VALUES
  (
    (
      SELECT
        uuid
      from
        public.users
      WHERE
        users.handle = 'philoxrud'
      LIMIT
        1
    ), 'This was imported as seed data!', current_timestamp + interval '10 day'
  )