-- Teachers assigned to a class may schedule its teaching sessions. The helper
-- already requires an active Teacher membership and a current class assignment.
begin;

drop policy if exists class_sessions_manager_insert on public.class_sessions;
drop policy if exists class_sessions_teacher_insert on public.class_sessions;
create policy class_sessions_teacher_insert
on public.class_sessions for insert to authenticated
with check (private.can_teach_class(class_id));

drop policy if exists classes_manager_update on public.classes;
create policy classes_manager_update
on public.classes for update to authenticated
using (private.can_manage_class(id))
with check (private.can_manage_class(id));

commit;
