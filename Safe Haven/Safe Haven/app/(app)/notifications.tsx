import React, { useEffect, useState } from 'react';
import { ActivityIndicator, Alert, FlatList, Image, StyleSheet, Text, View, Pressable } from 'react-native';
import { Stack } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { supabase } from '../../src/lib/supabase';
import { useAuth } from '../../src/providers/AuthProvider';

type AlertEvent = {
    id: string;
    type: string;
    confidence: number;
    created_at: string;
    status: string;
    person_name?: string | null;
    photo_url?: string | null;
};

export default function NotificationsScreen() {
    const { session } = useAuth();
    const [alerts, setAlerts] = useState<AlertEvent[]>([]);
    const [requesting, setRequesting] = useState(false);

    const requestLivePhoto = async () => {
        if (!session) return;
        setRequesting(true);
        try {
            const { data: hh } = await supabase
                .from('households')
                .select('id')
                .eq('owner_id', session.user.id)
                .limit(1);
            const householdId = hh && hh.length ? hh[0].id : null;
            if (!householdId) {
                Alert.alert('No camera', 'Add a family member first so your home is set up.');
                return;
            }
            const { error } = await supabase.from('photo_requests').insert({
                household_id: householdId,
                requested_by: session.user.id,
            });
            if (error) {
                Alert.alert('Request failed', error.message);
            } else {
                Alert.alert('Photo requested', 'A live photo will appear here in a few seconds (the camera must be running).');
            }
        } finally {
            setRequesting(false);
        }
    };

    const fetchAlerts = async () => {
        const { data, error } = await supabase
            .from('alerts')
            .select('*')
            .order('created_at', { ascending: false })
            .limit(50);

        if (error) {
            console.error('[Safe Haven Alerts] Fetch error:', error);
        } else if (data) {
            setAlerts(data as AlertEvent[]);
        }
    };

    const deleteAlert = async (id: string) => {
        try {
            const { error } = await supabase
                .from('alerts')
                .delete()
                .eq('id', id);
            if (error) throw error;
            setAlerts((prev) => prev.filter((a) => a.id !== id));
        } catch (err) {
            console.error('[Safe Haven Alerts] Delete error:', err);
        }
    };

    useEffect(() => {
        fetchAlerts();

        const channel = supabase
            .channel('alerts-channel')
            .on(
                'postgres_changes',
                { event: 'INSERT', schema: 'public', table: 'alerts' },
                (payload) => {
                    console.log('New Alert Received!', payload);
                    const newAlert = payload.new as AlertEvent;
                    setAlerts((prev) => {
                        if (prev.find((a) => a.id === newAlert.id)) return prev;
                        return [newAlert, ...prev];
                    });
                }
            )
            .on(
                'postgres_changes',
                { event: 'DELETE', schema: 'public', table: 'alerts' },
                (payload) => {
                    const deletedId = payload.old.id;
                    setAlerts((prev) => prev.filter((a) => a.id !== deletedId));
                }
            )
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, []);

    const renderItem = ({ item }: { item: AlertEvent }) => {
        const typeStr = item.type || '';
        const typeLower = typeStr.toLowerCase();
        const isFall = typeLower.includes('fall');
        const isHelp = typeLower.includes('help') || typeLower.includes('gesture');
        const timeString = new Date(item.created_at).toLocaleTimeString();

        // Format user-friendly display titles depending on the alert source
        let displayTitle = typeStr;
        if (typeStr === 'IMMEDIATE_HELP_REQUEST') {
            displayTitle = item.person_name ? `${item.person_name} requested immediate help` : 'Immediate Help Request';
        } else if (isFall) {
            displayTitle = '🚨 Fall Detected – Immediate Attention May Be Required';
        } else if (isHelp) {
            displayTitle = '⚠️ Emergency Help Gesture Detected – Immediate Attention Required';
        }

        const isFaceRecognition = typeLower.includes('door') || typeLower.includes('visitor') || typeLower.includes('face') || typeLower.includes('recognition');
        const isUnknown = item.person_name?.toLowerCase() === 'unknown' || typeLower.includes('unknown');
        const showEmergencyBadge = !isFaceRecognition || isUnknown;

        return (
            <View style={[
                styles.card,
                isFall && styles.cardFall,
                isHelp && styles.cardHelp
            ]}>
                <View style={styles.cardHeader}>
                    <View style={{ flex: 1, paddingRight: 8 }}>
                        <Text style={styles.cardType}>{displayTitle}</Text>
                        <Text style={styles.cardTime}>{timeString}</Text>
                    </View>
                    <Pressable
                        style={({ pressed }) => [styles.deleteBtn, pressed && { opacity: 0.7 }]}
                        onPress={() => deleteAlert(item.id)}
                    >
                        <Ionicons name="trash-outline" size={18} color="#FF3B30" />
                    </Pressable>
                </View>
                {item.photo_url ? (
                    <Image source={{ uri: item.photo_url }} style={styles.photo} resizeMode="contain" />
                ) : null}
                <View style={styles.badgeContainer}>
                    {showEmergencyBadge ? (
                        <View style={styles.badge}>
                            <Text style={styles.badgeText}>EMERGENCY</Text>
                        </View>
                    ) : (
                        <View style={[styles.badge, styles.badgeSafe]}>
                            <Text style={[styles.badgeText, styles.badgeTextSafe]}>KNOWN VISIT</Text>
                        </View>
                    )}
                    <Text style={styles.confidence}>
                        Confidence: {(item.confidence * 100).toFixed(0)}%
                    </Text>
                </View>
            </View>
        );
    };

    return (
        <View style={styles.container}>
            <Stack.Screen options={{ title: 'Live Cloud Alerts' }} />

            <View style={[styles.statusBanner, styles.statusOk]}>
                <Text style={styles.statusText}>● Connected to Safe Haven Cloud</Text>
            </View>

            <Pressable
                style={({ pressed }) => [styles.requestBtn, pressed && { opacity: 0.85 }]}
                onPress={requestLivePhoto}
                disabled={requesting}
            >
                {requesting ? (
                    <ActivityIndicator color="#fff" />
                ) : (
                    <>
                        <Ionicons name="camera" size={18} color="#fff" />
                        <Text style={styles.requestBtnText}>Request live photo</Text>
                    </>
                )}
            </Pressable>

            <FlatList
                data={alerts}
                renderItem={renderItem}
                keyExtractor={(item) => item.id}
                contentContainerStyle={styles.list}
                ListEmptyComponent={
                    <View style={styles.emptyState}>
                        <Text style={styles.emptyText}>No alerts yet.</Text>
                        <Text style={styles.emptySubText}>
                            Monitoring devices via Supabase...
                        </Text>
                    </View>
                }
            />
        </View>
    );
}

const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#f5f5f5' },
    statusBanner: {
        padding: 12,
        borderBottomWidth: 1,
        borderBottomColor: '#ddd',
    },
    statusOk: { backgroundColor: '#e8f5e9' },
    statusText: { fontWeight: '700', fontSize: 14, color: '#333' },
    list: { padding: 16 },
    card: {
        backgroundColor: 'white',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        borderLeftWidth: 6,
        borderLeftColor: '#999',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    cardFall: { borderLeftColor: '#ff3b30' },
    cardHelp: { borderLeftColor: '#ff9500' },
    cardHeader: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 8 },
    cardType: { fontSize: 18, fontWeight: '800', color: '#333' },
    cardTime: { fontSize: 14, color: '#666' },
    badgeContainer: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
    badge: { backgroundColor: '#ffebee', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4 },
    badgeText: { color: '#d32f2f', fontWeight: '700', fontSize: 12 },
    badgeSafe: { backgroundColor: '#e8f5e9' },
    badgeTextSafe: { color: '#2e7d32' },
    deleteBtn: {
        padding: 6,
        borderRadius: 8,
        backgroundColor: '#FFF5F5',
        alignItems: 'center',
        justifyContent: 'center',
    },
    confidence: { fontSize: 12, color: '#888' },
    photo: { width: '100%', aspectRatio: 4 / 3, borderRadius: 10, marginBottom: 10, backgroundColor: '#000' },
    requestBtn: {
        flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
        backgroundColor: '#0A84FF', marginHorizontal: 16, marginTop: 12,
        paddingVertical: 14, borderRadius: 12,
    },
    requestBtnText: { color: '#fff', fontWeight: '800', fontSize: 15 },
    emptyState: { padding: 40, alignItems: 'center' },
    emptyText: { fontSize: 18, fontWeight: '600', color: '#888', marginBottom: 8 },
    emptySubText: { textAlign: 'center', color: '#aaa' },
});
