import React, { useState } from "react";
import { View, Text, ScrollView, Pressable, RefreshControl } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/src/api";
import { useTheme, spacing, radius } from "@/src/theme";
import { Icon, T, Card, Button, Loading, ErrorState, Empty, Sheet, Field } from "@/src/ui";
import { Header } from "@/src/screen";

function startOfMonth(d: Date) { return new Date(d.getFullYear(), d.getMonth(), 1); }

export default function Calendar() {
  const insets = useSafeAreaInsets();
  const { colors } = useTheme();
  const qc = useQueryClient();
  const [cursor, setCursor] = useState(new Date());
  const [selected, setSelected] = useState(new Date());
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [time, setTime] = useState("15:00");

  const { data, isLoading, isError, refetch, isRefetching } = useQuery({ queryKey: ["events"], queryFn: () => api.get("/events") });
  const save = useMutation({ mutationFn: (b: any) => api.post("/events", b), onSuccess: () => { qc.invalidateQueries({ queryKey: ["events"] }); qc.invalidateQueries({ queryKey: ["dashboard"] }); setOpen(false); setTitle(""); } });

  const first = startOfMonth(cursor);
  const startDay = first.getDay();
  const daysInMonth = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 0).getDate();
  const cells: (number | null)[] = [...Array(startDay).fill(null), ...Array.from({ length: daysInMonth }, (_, i) => i + 1)];

  const events = data || [];
  const eventsOn = (day: number) => events.filter((e: any) => {
    const d = new Date(e.start);
    return d.getFullYear() === cursor.getFullYear() && d.getMonth() === cursor.getMonth() && d.getDate() === day;
  });
  const selEvents = events.filter((e: any) => new Date(e.start).toDateString() === selected.toDateString())
    .sort((a: any, b: any) => a.start.localeCompare(b.start));

  return (
    <View style={{ flex: 1, backgroundColor: colors.surface }}>
      <Header title="Calendar" back showSearch={false} />
      {isLoading ? <Loading /> : isError ? <ErrorState onRetry={refetch} /> : (
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: insets.bottom + 80 }}
          refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.brandPrimary} />}>
          <Card>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <Pressable testID="cal-prev" onPress={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1))}><Icon name="chevron-left" size={26} /></Pressable>
              <T size={17} weight="800">{cursor.toLocaleString([], { month: "long", year: "numeric" })}</T>
              <Pressable testID="cal-next" onPress={() => setCursor(new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1))}><Icon name="chevron-right" size={26} /></Pressable>
            </View>
            <View style={{ flexDirection: "row" }}>
              {["S", "M", "T", "W", "T", "F", "S"].map((d, i) => <Text key={i} style={{ flex: 1, textAlign: "center", color: colors.muted, fontWeight: "700", fontSize: 12 }}>{d}</Text>)}
            </View>
            <View style={{ flexDirection: "row", flexWrap: "wrap", marginTop: 8 }}>
              {cells.map((c, i) => {
                if (c === null) return <View key={i} style={{ width: `${100 / 7}%`, height: 44 }} />;
                const date = new Date(cursor.getFullYear(), cursor.getMonth(), c);
                const isSel = date.toDateString() === selected.toDateString();
                const isToday = date.toDateString() === new Date().toDateString();
                const has = eventsOn(c).length > 0;
                return (
                  <Pressable key={i} testID={`cal-day-${c}`} onPress={() => setSelected(date)} style={{ width: `${100 / 7}%`, height: 44, alignItems: "center", justifyContent: "center" }}>
                    <View style={{ width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center", backgroundColor: isSel ? colors.brandPrimary : "transparent", borderWidth: isToday && !isSel ? 1.5 : 0, borderColor: colors.brandPrimary }}>
                      <Text style={{ color: isSel ? "#fff" : colors.onSurface, fontWeight: isToday ? "800" : "500" }}>{c}</Text>
                    </View>
                    {has ? <View style={{ width: 5, height: 5, borderRadius: 3, backgroundColor: isSel ? colors.brandPrimary : colors.brandSecondary, marginTop: 1 }} /> : null}
                  </Pressable>
                );
              })}
            </View>
          </Card>

          <T size={16} weight="800" style={{ marginTop: 18, marginBottom: 8 }}>{selected.toLocaleDateString([], { weekday: "long", day: "numeric", month: "long" })}</T>
          {selEvents.length === 0 ? <Empty icon="calendar-blank-outline" title="No events" subtitle="Tap + to add an event." /> :
            selEvents.map((e: any) => (
              <Card key={e.id} style={{ marginBottom: 10, flexDirection: "row", gap: 12 }}>
                <View style={{ width: 4, borderRadius: 2, backgroundColor: colors.brandPrimary }} />
                <View style={{ flex: 1 }}>
                  <T size={15} weight="700">{e.title}</T>
                  <T size={13} color={colors.muted}>{new Date(e.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}{e.location ? ` · ${e.location}` : ""}</T>
                  {(e.attendees || []).length ? <T size={12} color={colors.muted} style={{ marginTop: 2 }}>{e.attendees.length} guest(s)</T> : null}
                </View>
                {e.location === "Fmail Meet" ? <Icon name="video-outline" size={22} color={colors.brandPrimary} /> : null}
              </Card>
            ))}
        </ScrollView>
      )}
      <Pressable testID="event-fab" onPress={() => setOpen(true)} style={{ position: "absolute", right: 20, bottom: insets.bottom + 16, width: 58, height: 58, borderRadius: 20, backgroundColor: colors.brandPrimary, alignItems: "center", justifyContent: "center", elevation: 6 }}>
        <Icon name="plus" size={28} color="#fff" />
      </Pressable>
      <Sheet visible={open} onClose={() => setOpen(false)} title="New event" testID="event-sheet">
        <Field placeholder="Event title" value={title} onChangeText={setTitle} testID="event-title" />
        <T size={13} weight="700" color={colors.muted} style={{ marginTop: 14, marginBottom: 6 }}>TIME (HH:MM)</T>
        <Field placeholder="15:00" value={time} onChangeText={setTime} testID="event-time" />
        <T size={13} color={colors.muted} style={{ marginTop: 10 }}>On {selected.toLocaleDateString([], { day: "numeric", month: "long" })}</T>
        <Button title="Add event" icon="plus" testID="event-save" onPress={() => {
          const [h, m] = time.split(":");
          const d = new Date(selected); d.setHours(parseInt(h) || 9, parseInt(m) || 0, 0, 0);
          if (title.trim()) save.mutate({ title, start: d.toISOString(), location: "Fmail Meet" });
        }} style={{ marginTop: 20 }} />
      </Sheet>
    </View>
  );
}
