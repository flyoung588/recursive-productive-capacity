import { Kysely } from 'kysely';

// The optional SUMMARY_ASSISTANT config must not be passed as an undefined
// database DEFAULT. Without this guard a clean local migration crashes
// with "invalid immediate value undefined" in Kysely.
export async function up(db: Kysely<any>) {
  const defaultAssistant = process.env.SUMMARY_ASSISTANT;

  await db.schema
    .alterTable('workspaces')
    .addColumn('summary_assistant_id', 'text', (col) =>
      defaultAssistant === undefined ? col : col.defaultTo(defaultAssistant),
    )
    .execute();

  await db.schema
    .alterTable('host_db')
    .addColumn('summary_assistant_id', 'text', (col) =>
      defaultAssistant === undefined ? col : col.defaultTo(defaultAssistant),
    )
    .execute();
}

export async function down(db: Kysely<any>) {
  await db.schema
    .alterTable('workspaces')
    .dropColumn('summary_assistant_id')
    .execute();

  await db.schema
    .alterTable('host_db')
    .dropColumn('summary_assistant_id')
    .execute();
}
