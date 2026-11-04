-- Caller owns target confirmation/transaction. Never discard recorded decisions.
LOCK TABLE public.household_head_assignments,public.household_member_relationships IN ACCESS EXCLUSIVE MODE;
DO $guard$ BEGIN
 IF EXISTS(SELECT 1 FROM public.household_head_assignments)
    OR EXISTS(SELECT 1 FROM public.household_member_relationships) THEN
   RAISE EXCEPTION 'Rollback refused: preserve recorded household-head decisions; roll back application code only';
 END IF;
END $guard$;
DROP TABLE public.household_member_relationships;
DROP TABLE public.household_head_assignments;
ALTER TABLE public.household DROP CONSTRAINT household_resident_home_identity;
