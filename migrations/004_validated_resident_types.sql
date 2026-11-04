-- Existing incompatible data is rejected by explicit preflight, never deleted or guessed.
ALTER TABLE household ALTER COLUMN birthdate TYPE DATE USING NULLIF(TRIM(birthdate::text),'')::date;
ALTER TABLE household ADD CONSTRAINT resident_firstname_required CHECK (firstname IS NOT NULL AND length(trim(firstname))>0);
ALTER TABLE household ADD CONSTRAINT resident_surname_required CHECK (surname IS NOT NULL AND length(trim(surname))>0);
ALTER TABLE household ADD CONSTRAINT resident_household_required CHECK (household_id IS NOT NULL);
ALTER TABLE household ADD CONSTRAINT resident_gender_allowed CHECK (gender IS NULL OR gender IN ('Male','Female','Not recorded'));
ALTER TABLE household ADD CONSTRAINT resident_status_allowed CHECK (status IS NULL OR status IN ('Active','Deceased'));
ALTER TABLE household ADD CONSTRAINT resident_civil_allowed CHECK (civil_status IS NULL OR civil_status IN ('Single','Married','Widowed','Separated','Not recorded'));
ALTER TABLE household ADD CONSTRAINT resident_birthdate_not_future CHECK (birthdate IS NULL OR birthdate<=(CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::date);
ALTER TABLE household ADD CONSTRAINT resident_death_valid CHECK (death_date IS NULL OR (status='Deceased' AND death_date<=(CURRENT_TIMESTAMP AT TIME ZONE 'Asia/Manila')::date AND (birthdate IS NULL OR death_date>=birthdate)));
