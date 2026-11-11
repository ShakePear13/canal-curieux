-- Canal Curieux : base de synchronisation (vues, « plus tard », 👍/👎, réglages, chaînes).
-- À coller une seule fois dans Supabase > SQL Editor, après avoir remplacé MON-CODE-DE-SYNCHRO
-- (tout en bas) par ton code personnel. Ce code sert de mot de passe : garde-le pour toi.

create table if not exists public.cc_etat (
  cle     text primary key,                 -- empreinte du code de synchro (jamais le code lui-même)
  donnees jsonb not null default '{}'::jsonb,
  maj     timestamptz not null default now()
);

-- Personne ne peut lire ni écrire la table directement : tout passe par les deux fonctions ci-dessous.
alter table public.cc_etat enable row level security;
revoke all on public.cc_etat from anon, authenticated;

create or replace function public.cc_lire(p_code text)
returns jsonb language sql security definer set search_path = public as $$
  select donnees from public.cc_etat
  where cle = encode(sha256(convert_to(p_code, 'UTF8')), 'hex');
$$;

create or replace function public.cc_ecrire(p_code text, p_donnees jsonb)
returns boolean language plpgsql security definer set search_path = public as $$
begin
  if octet_length(p_donnees::text) > 1000000 then
    raise exception 'donnees trop volumineuses';
  end if;
  update public.cc_etat set donnees = p_donnees, maj = now()
  where cle = encode(sha256(convert_to(p_code, 'UTF8')), 'hex');
  return found;
end;
$$;

revoke all on function public.cc_lire(text) from public;
revoke all on function public.cc_ecrire(text, jsonb) from public;
grant execute on function public.cc_lire(text) to anon, authenticated;
grant execute on function public.cc_ecrire(text, jsonb) to anon, authenticated;

-- Ton code de synchro (au moins 16 caractères, sans apostrophe) :
insert into public.cc_etat (cle)
values (encode(sha256(convert_to('MON-CODE-DE-SYNCHRO', 'UTF8')), 'hex'))
on conflict do nothing;
