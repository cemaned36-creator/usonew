export type LessonParticipant = {
  group_id: number;
  group_name: string;
  subgroup_number: number;
  students_count: number;
};

export function formatParticipants(
  participants: LessonParticipant[] | undefined,
): string {
  if (!participants?.length) {
    return "Участники не загружены";
  }

  return participants
    .map((member) =>
      member.subgroup_number === 0
        ? member.group_name
        : `${member.group_name} (${member.subgroup_number}-я подгруппа)`,
    )
    .join(", ");
}