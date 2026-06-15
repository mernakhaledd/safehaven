import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  StyleSheet,
  Text,
  View,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  Alert,
  BackHandler,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useLocalSearchParams, router } from 'expo-router';

import { Screen } from '../../../src/components/ui/Screen';
import { Button } from '../../../src/components/ui/Button';
import { Colors } from '../../../src/theme/colors';
import { useAuth } from '../../../src/providers/AuthProvider';
import { useProfile } from '../../../src/providers/ProfileProvider';
import { supabase } from '../../../src/lib/supabase';

type ConversationPreview = {
  id: string;
  title: string;
  lastMessage: string;
  updatedAt: string;
};

type DbMsg = {
  id: string;
  sender_profile_id: string;
  body: string;
  created_at: string;
};

export default function CaregiverChats() {
  const { session } = useAuth();
  const { activeProfile, textSize, highContrast } = useProfile();
  const { autoOpen } = useLocalSearchParams<{ autoOpen?: string }>();
  
  // List state
  const [conversations, setConversations] = useState<ConversationPreview[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  
  // Active chat state
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [partnerName, setPartnerName] = useState<string>('');
  const [messagesList, setMessagesList] = useState<DbMsg[]>([]);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [draft, setDraft] = useState('');
  const [sending, setSending] = useState(false);
  
  const flatListRef = useRef<FlatList>(null);

  const fontScale = textSize === 'large' ? 1.25 : textSize === 'xl' ? 1.5 : 1.0;
  const dynamicText = (baseSize: number) => ({
    fontSize: baseSize * fontScale,
    ...(highContrast ? { color: '#000000', fontWeight: 'bold' as const } : {}),
  });
  const dynamicBg = (style: object) => [
    style,
    highContrast && { backgroundColor: '#ffffff', borderColor: '#000000', borderWidth: 2 },
  ];

  // 1. Fetch Master List of Conversations
  const loadConversations = useCallback(async (silent = false) => {
    if (!activeProfile || !session) {
      setConversations([]);
      setLoadingList(false);
      return;
    }
    if (!silent) setLoadingList(true);

    try {
      const { data: partners, error: partnersError } = await supabase
        .from('profiles')
        .select('id, display_name')
        .eq('user_id', session.user.id)
        .eq('persona', 'care_receiver');

      if (partnersError || !partners || partners.length === 0) {
        setConversations([]);
        setLoadingList(false);
        return;
      }

      const { data: convs } = await supabase
        .from('conversations')
        .select('id, care_receiver_profile_id')
        .eq('care_giver_profile_id', activeProfile.id);

      const list: ConversationPreview[] = [];
      const tempDates: { [key: string]: string } = {};

      for (const partner of partners) {
        const conv = (convs ?? []).find((c) => c.care_receiver_profile_id === partner.id);
        let conversationId = conv?.id;

        if (!conversationId) {
          const { data: rpcId, error: rpcErr } = await supabase.rpc('get_or_create_conversation', {
            p_giver_profile_id: activeProfile.id,
            p_receiver_profile_id: partner.id,
          });
          if (!rpcErr && rpcId) conversationId = rpcId as string;
        }

        if (conversationId) {
          const { data: lastMsg } = await supabase
            .from('messages')
            .select('body, created_at')
            .eq('conversation_id', conversationId)
            .order('created_at', { ascending: false })
            .limit(1)
            .maybeSingle();

          list.push({
            id: conversationId,
            title: partner.display_name,
            lastMessage: lastMsg?.body ?? 'No messages yet.',
            updatedAt: lastMsg?.created_at
              ? new Date(lastMsg.created_at).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                })
              : 'New',
          });

          tempDates[conversationId] = lastMsg?.created_at ?? '';
        }
      }

      list.sort((a, b) => {
        const dateA = tempDates[a.id] || '';
        const dateB = tempDates[b.id] || '';
        return dateB.localeCompare(dateA);
      });

      setConversations(list);
    } catch (err) {
      console.error('[Safe Haven] failed to load caregiver conversations', err);
    } finally {
      if (!silent) setLoadingList(false);
    }
  }, [activeProfile, session]);

  // 2. Fetch Active Chat Messages
  const fetchMessages = useCallback(async (convId: string) => {
    setLoadingMessages(true);
    try {
      const { data, error } = await supabase
        .from('messages')
        .select('id, sender_profile_id, body, created_at')
        .eq('conversation_id', convId)
        .order('created_at', { ascending: false });

      if (!error && data) {
        setMessagesList(data as DbMsg[]);
      }
    } catch (e) {
      console.error('[Safe Haven] failed to fetch messages', e);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // 3. Send Message Handler
  async function handleSend() {
    if (!draft.trim() || !session || !activeProfile || !activeConversationId || sending) return;
    setSending(true);
    const body = draft.trim();
    setDraft('');

    try {
      const { error } = await supabase.from('messages').insert({
        user_id: session.user.id,
        conversation_id: activeConversationId,
        sender_profile_id: activeProfile.id,
        body,
      });

      if (error) throw error;

      await supabase
        .from('conversations')
        .update({ updated_at: new Date().toISOString() })
        .eq('id', activeConversationId);

    } catch (e) {
      console.error('[Safe Haven] send failed', e);
      Alert.alert('Error', 'Failed to send message.');
      setDraft(body);
    } finally {
      setSending(false);
    }
  }

  // Load conversations list initially
  useEffect(() => {
    loadConversations();
  }, [activeProfile?.id]);

  useEffect(() => {
    if (autoOpen && conversations.length > 0) {
      const found = conversations.find((c) => c.id === autoOpen);
      if (found) {
        setActiveConversationId(autoOpen);
        setPartnerName(found.title);
      }
    }
  }, [autoOpen, conversations]);

  // Listen to global chats updates (master list refresh)
  useEffect(() => {
    const channel = supabase
      .channel('caregiver_chats_list_realtime')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'messages' }, () => loadConversations(true))
      .on('postgres_changes', { event: '*', schema: 'public', table: 'conversations' }, () => loadConversations(true))
      .subscribe();
    return () => { supabase.removeChannel(channel); };
  }, [loadConversations]);

  // Handle back button press to close active conversation
  useEffect(() => {
    const onBackPress = () => {
      if (activeConversationId) {
        closeChat();
        return true; // prevent default back navigation
      }
      return false; // allow default back navigation
    };

    const subscription = BackHandler.addEventListener('hardwareBackPress', onBackPress);
    return () => {
      subscription.remove();
    };
  }, [activeConversationId]);

  // Handle active conversation load and real-time messaging channel
  useEffect(() => {
    if (!activeConversationId) {
      setMessagesList([]);
      return;
    }
    fetchMessages(activeConversationId);

    const channel = supabase
      .channel(`chat_thread_${activeConversationId}`)
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'messages',
          filter: `conversation_id=eq.${activeConversationId}`,
        },
        (payload) => {
          const newMsg = payload.new as DbMsg;
          setMessagesList((prev) => {
            if (prev.find((m) => m.id === newMsg.id)) return prev;
            return [newMsg, ...prev];
          });
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [activeConversationId, fetchMessages]);

  const selectChat = (convId: string, title: string) => {
    setPartnerName(title);
    setActiveConversationId(convId);
  };

  const closeChat = () => {
    setActiveConversationId(null);
    setPartnerName('');
    router.setParams({ autoOpen: '' });
    loadConversations(true);
  };

  // Render Inline Chat View
  if (activeConversationId) {
    return (
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        <Screen style={{ paddingBottom: 0, backgroundColor: highContrast ? '#ffffff' : undefined }}>
          {/* Header Area */}
          <View style={[styles.chatHeader, highContrast && { borderBottomWidth: 2, borderColor: '#000' }]}>
            <Pressable style={styles.backBtn} onPress={closeChat}>
              <Ionicons name="arrow-back" size={22} color={highContrast ? '#000' : Colors.primary} />
              <Text style={[styles.backText, dynamicText(15), { color: highContrast ? '#000' : Colors.primary }]}>Back</Text>
            </Pressable>
            <View style={styles.headerTitleWrap}>
              <Text style={[styles.chatPartnerName, dynamicText(18)]}>{partnerName}</Text>
              <Text style={[styles.headerSubtitle, dynamicText(11), { color: Colors.muted }]}>Care Receiver</Text>
            </View>
            <View style={{ width: 60 }} />
          </View>

          {loadingMessages ? (
            <View style={styles.center}>
              <ActivityIndicator size="large" color={Colors.primary} />
            </View>
          ) : (
            <FlatList
              ref={flatListRef}
              style={{ flex: 1 }}
              data={messagesList}
              keyExtractor={(m) => m.id}
              contentContainerStyle={{ gap: 10, paddingTop: 10, paddingBottom: 14 }}
              inverted
              ListEmptyComponent={
                <View style={styles.center}>
                  <Text style={[styles.emptyText, dynamicText(14)]}>No messages yet. Say hi!</Text>
                </View>
              }
              renderItem={({ item }) => {
                const isMine = item.sender_profile_id === activeProfile?.id;
                const timeString = new Date(item.created_at).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                });

                return (
                  <View style={[styles.bubble, isMine ? styles.mine : styles.theirs, highContrast && { borderWidth: 2, borderColor: '#000' }]}>
                    <Text style={[styles.bodyText, dynamicText(14), isMine ? { color: '#fff' } : { color: Colors.text }]}>
                      {item.body}
                    </Text>
                    <Text style={[styles.time, dynamicText(9), isMine ? { color: 'rgba(255,255,255,0.75)' } : { color: Colors.muted }]}>
                      {timeString}
                    </Text>
                  </View>
                );
              }}
            />
          )}

          {/* Message input composer */}
          <View style={[styles.composer, highContrast && { borderWidth: 2, borderColor: '#000' }]}>
            <TextInput
              value={draft}
              onChangeText={setDraft}
              placeholder="Type a message…"
              placeholderTextColor={Colors.muted}
              style={[styles.input, highContrast && { borderColor: '#000' }]}
              onSubmitEditing={handleSend}
              returnKeyType="send"
            />
            <Button
              title={sending ? '...' : 'Send'}
              size="md"
              disabled={!draft.trim() || sending}
              onPress={handleSend}
              style={highContrast ? { borderWidth: 2, borderColor: '#000' } : undefined}
            />
          </View>
        </Screen>
      </KeyboardAvoidingView>
    );
  }

  // Render Master Conversations List View
  return (
    <Screen style={{ backgroundColor: highContrast ? '#ffffff' : undefined }}>
      <Text style={[styles.title, dynamicText(26)]}>Chats</Text>

      {loadingList && conversations.length === 0 ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : conversations.length === 0 ? (
        <View style={styles.center}>
          <Ionicons name="chatbubbles-outline" size={48} color={Colors.muted} />
          <Text style={[styles.emptyTitle, dynamicText(18)]}>No chats yet</Text>
          <Text style={[styles.emptyText, dynamicText(14)]}>Linked care receivers will show up here to chat.</Text>
        </View>
      ) : (
        <FlatList
          data={conversations}
          keyExtractor={(i) => i.id}
          contentContainerStyle={{ gap: 12, paddingTop: 14 }}
          renderItem={({ item }) => (
            <Pressable
              style={({ pressed }) => [
                dynamicBg(styles.row),
                pressed && { opacity: 0.9, transform: [{ scale: 0.995 }] },
              ]}
              onPress={() => selectChat(item.id, item.title)}
            >
              <View style={styles.rowHeader}>
                <Text style={[styles.rowTitle, dynamicText(16)]}>{item.title}</Text>
                <Text style={[styles.rowMeta, dynamicText(12)]}>{item.updatedAt}</Text>
              </View>
              <Text style={[styles.rowBody, dynamicText(14)]} numberOfLines={1}>
                {item.lastMessage}
              </Text>
            </Pressable>
          )}
        />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontSize: 26, fontWeight: '900', color: Colors.text, marginBottom: 4 },
  row: {
    backgroundColor: Colors.card,
    borderColor: Colors.border,
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOpacity: 0.02,
    shadowRadius: 6,
    shadowOffset: { width: 0, height: 2 },
  },
  rowHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  rowTitle: { fontSize: 16, fontWeight: '800', color: Colors.text },
  rowBody: { color: Colors.muted, fontSize: 14, fontWeight: '500' },
  rowMeta: { color: Colors.muted, fontSize: 12, fontWeight: '700' },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 24, gap: 8 },
  emptyTitle: { fontWeight: '900', color: Colors.text, fontSize: 18, marginTop: 12 },
  emptyText: { color: Colors.muted, textAlign: 'center', fontSize: 14 },
  
  // Chat styling details
  chatHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#E2E8F0',
    marginBottom: 4,
  },
  backBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 4,
    width: 60,
  },
  backText: { fontWeight: '700' },
  headerTitleWrap: {
    alignItems: 'center',
    flex: 1,
  },
  chatPartnerName: { fontWeight: '900', color: Colors.text },
  headerSubtitle: { fontWeight: '600', marginTop: 1 },
  bubble: {
    maxWidth: '80%',
    borderRadius: 16,
    paddingVertical: 10,
    paddingHorizontal: 14,
  },
  mine: {
    alignSelf: 'flex-end',
    backgroundColor: Colors.primary,
    borderBottomRightRadius: 2,
  },
  theirs: {
    alignSelf: 'flex-start',
    backgroundColor: '#F1F5F9',
    borderBottomLeftRadius: 2,
  },
  bodyText: { fontWeight: '600', lineHeight: 20 },
  time: { marginTop: 4, fontWeight: '700', alignSelf: 'flex-end' },
  composer: {
    flexDirection: 'row',
    gap: 8,
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: Colors.border,
    backgroundColor: Colors.white,
    borderRadius: 18,
    marginVertical: 10,
  },
  input: {
    flex: 1,
    backgroundColor: '#F8FAFC',
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 14,
    fontSize: 16,
    color: Colors.text,
    borderWidth: 1,
    borderColor: '#E2E8F0',
  },
});
