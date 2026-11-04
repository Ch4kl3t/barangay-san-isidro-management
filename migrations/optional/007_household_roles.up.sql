-- Separately approved additive feature migration, after canonical 001-006.
-- Caller owns transaction, target pinning and advisory lock 762022.
-- No baseline row, account, role, health value or date is updated/backfilled.
ALTER TABLE public.household ADD CONSTRAINT household_resident_home_identity UNIQUE(id,household_id);
CREATE TABLE public.household_head_assignments (
 id BIGSERIAL PRIMARY KEY,
 household_id INTEGER REFERENCES public.households(id) ON DELETE SET NULL,
 household_id_record INTEGER NOT NULL,
 resident_id INTEGER,
 resident_id_record INTEGER NOT NULL,
 assigned_by INTEGER REFERENCES public.users(id) ON DELETE SET NULL,
 assigned_by_record INTEGER NOT NULL,
 reason VARCHAR(300) NOT NULL CHECK (length(trim(reason)) BETWEEN 3 AND 300),
 assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 ended_at TIMESTAMP,
 UNIQUE(id,household_id),
 CHECK (ended_at IS NULL OR ended_at>=assigned_at),
 CHECK (resident_id IS NULL OR household_id IS NOT NULL),
 FOREIGN KEY(resident_id,household_id) REFERENCES public.household(id,household_id)
   ON UPDATE RESTRICT ON DELETE SET NULL(resident_id)
);
CREATE UNIQUE INDEX household_head_current ON public.household_head_assignments(household_id) WHERE ended_at IS NULL;
CREATE UNIQUE INDEX resident_head_current ON public.household_head_assignments(resident_id) WHERE ended_at IS NULL;
CREATE TABLE public.household_member_relationships (
 assignment_id BIGINT NOT NULL REFERENCES public.household_head_assignments(id) ON DELETE RESTRICT,
 resident_id INTEGER,
 household_id INTEGER REFERENCES public.households(id) ON DELETE SET NULL,
 resident_id_record INTEGER NOT NULL,
 relationship VARCHAR(80) NOT NULL CHECK (length(trim(relationship)) BETWEEN 1 AND 80 AND lower(trim(relationship))<>'head'),
 PRIMARY KEY(assignment_id,resident_id_record),
 FOREIGN KEY(assignment_id,household_id) REFERENCES public.household_head_assignments(id,household_id),
 CHECK (resident_id IS NULL OR household_id IS NOT NULL),
 FOREIGN KEY(resident_id,household_id) REFERENCES public.household(id,household_id)
   ON UPDATE RESTRICT ON DELETE SET NULL(resident_id)
);
CREATE INDEX household_relationship_resident ON public.household_member_relationships(resident_id);
