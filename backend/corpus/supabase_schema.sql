-- Run this in the Supabase SQL editor to set up the cases table

create table if not exists cases (
    id uuid primary key default gen_random_uuid(),
    case_type text not null,
    current_stage text not null,
    stage_start_date date not null,
    facts jsonb not null default '{}'::jsonb,
    history jsonb not null default '[]'::jsonb,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- Optional: keep updated_at fresh on every update
create or replace function set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists trg_cases_updated_at on cases;
create trigger trg_cases_updated_at
before update on cases
for each row
execute procedure set_updated_at();
