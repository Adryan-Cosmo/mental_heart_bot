from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, ReminderScheduled, ConversationPaused
from rasa_sdk.events import FollowupAction
from rasa_sdk import FormValidationAction
import datetime
import random
from datetime import timedelta

class MoodTrackerAction(Action):
    def name(self) -> Text:
        return "action_track_mood"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        mood = tracker.get_slot("current_mood")
        intensity = tracker.get_slot("mood_intensity")
        trigger = tracker.get_slot("mood_trigger")
        mood_history = tracker.get_slot("mood_history") or []
        
        if mood:
            # Garanta que a intensidade seja um inteiro para comparação
            try:
                intensity_val = int(intensity) if intensity else 0
            except (ValueError, TypeError):
                intensity_val = 0 # Valor padrão se a intensidade não for numérica

            new_entry = {
                "date": datetime.datetime.now().isoformat(),
                "mood": mood,
                "intensity": intensity_val, # Use o valor inteiro
                "trigger": trigger
            }
            mood_history.append(new_entry)
            
            analysis = self.analyze_mood_pattern(mood_history)
            
            dispatcher.utter_message(text=f"Seu humor foi registrado: {mood} (intensidade {intensity_val}/10)")
            
            if analysis:
                dispatcher.utter_message(text=analysis)
            
            # Sugere ajuda se intensidade alta
            if intensity_val >= 7: # Use o valor inteiro para comparação
                dispatcher.utter_message(text="Parece que você está se sentindo muito mal. Quer que eu indique recursos de ajuda profissional?")
            
            return [
                SlotSet("mood_history", mood_history),
                SlotSet("current_mood", None),
                SlotSet("mood_intensity", None),
                SlotSet("mood_trigger", None)
            ]
        else:
            dispatcher.utter_message(text="Por favor, me diga como você está se sentindo para registrar seu humor.")
            return []

    def analyze_mood_pattern(self, history):
        if len(history) < 3:
            return None
            
        recent = history[-3:]
        moods = [entry["mood"] for entry in recent]
        intensities = [entry.get("intensity", 0) for entry in recent] # Já é int aqui
        
        if all(m in ["depressed", "anxious", "stressed"] for m in moods):
            return "Notei que você está se sentindo mal nos últimos dias. Isso é preocupante."
        
        if all(i >= 7 for i in intensities):
            return "Você está passando por momentos intensos recentemente."
        
        return None

class EmergencyProtocolAction(Action):
    def name(self) -> Text:
        return "action_emergency_protocol"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        university = tracker.get_slot("university")
        resources = [
            "CVV - Centro de Valorização da Vida: Ligue 188 (24h, gratuito)",
            "CAPS - Centro de Atenção Psicossocial: Procure a unidade mais próxima"
        ]
        
        if university:
            resources.append(f"{university} - Serviço de Saúde Mental")
        
        dispatcher.utter_message(text="⚠️ Recursos de ajuda imediata:")
        for resource in resources:
            dispatcher.utter_message(text=f"• {resource}")
        
        dispatcher.utter_message(text="Você não está sozinho(a). Por favor, entre em contato com algum desses serviços.")
        
        return [ConversationPaused()]

class ActionSetReminder(Action):
    def name(self) -> Text:
        return "action_set_reminder"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        activity = tracker.get_slot("activity")
        time_slot = tracker.get_slot("time")
        date_slot = tracker.get_slot("date")
        
        if not activity:
            dispatcher.utter_message(text="Para que atividade você deseja um lembrete?")
            return []
        
        try:
            if date_slot and time_slot:
                reminder_time = datetime.datetime.now() + timedelta(hours=1)  # Simulação
            elif time_slot:
                reminder_time = datetime.datetime.now() + timedelta(hours=1)
            else:
                reminder_time = datetime.datetime.now() + timedelta(days=1)
            
            reminder = ReminderScheduled(
                "EXTERNAL_reminder",
                trigger_date_time=reminder_time,
                name=f"reminder_{activity}",
                entities=[{"entity": "activity", "value": activity}],
                kill_on_user_message=False,
            )
            
            dispatcher.utter_message(text=f"✅ Lembrete configurado para '{activity}' em {reminder_time.strftime('%d/%m às %H:%M')}.")
            
            return [
                reminder,
                SlotSet("activity", None),
                SlotSet("time", None),
                SlotSet("date", None)
            ]
            
        except Exception as e:
            dispatcher.utter_message(text="Não consegui entender o horário. Poderia especificar melhor?")
            return []
        
class MoodTrackingForm(FormValidationAction):
    def name(self) -> Text:
        return "mood_tracking_form"

    # Mude esta linha para incluir 'self' e 'tracker'
    def required_slots(self, tracker: Tracker) -> List[Text]: 
        return ["current_mood", "mood_intensity", "mood_trigger"]
    
    # O restante da classe MoodTrackingForm permanece como está
    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> List[Dict[Text, Any]]:
        # Este método `run` é para a ação customizada do formulário,
        # onde você pode adicionar lógica para o que acontece quando o formulário é ativado
        # e como ele pede os slots.
        # Por enquanto, ele apenas aciona a ação de rastreamento de humor ao final.
        
        # O Rasa já vai perguntar automaticamente pelos slots requeridos.
        # Você não precisa adicionar lógica explícita de "ask_<slot_name>" aqui,
        # a menos que queira customizar a mensagem de pergunta.
        
        # Quando todos os slots forem preenchidos, o formulário será desativado
        # e a ação `action_track_mood` será chamada.
        return [FollowupAction(name="action_track_mood")]

    # Você pode adicionar métodos de validação para cada slot aqui, se precisar.
    # Exemplo (se você tiver um slot 'current_mood' e quiser validar):
    def validate_current_mood(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        # Aqui você pode adicionar lógica de validação para o 'current_mood'
        # Por exemplo, verificar se o humor é válido (feliz, triste, etc.)
        # e retornar {"current_mood": slot_value} ou {"current_mood": None} para re-pedir
        return {"current_mood": slot_value}

    def validate_mood_intensity(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        try:
            intensity = int(slot_value)
            if 1 <= intensity <= 10:
                return {"mood_intensity": intensity}
            else:
                dispatcher.utter_message(text="Por favor, digite um número entre 1 e 10.")
                return {"mood_intensity": None}
        except ValueError:
            dispatcher.utter_message(text="Isso não parece ser um número. Por favor, digite a intensidade como um número de 1 a 10.")
            return {"mood_intensity": None}
    
    def validate_mood_trigger(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        # Aqui você pode adicionar lógica de validação para o 'mood_trigger'
        return {"mood_trigger": slot_value}

class ActionDefaultFallback(Action):
    def name(self) -> Text:
        return "action_default_fallback"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        dispatcher.utter_message(template="utter_fallback")
        return [ConversationPaused()]
    

class ActionTrackMood(Action):
    def name(self) -> Text:
        return "action_track_mood"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        current_mood = tracker.get_slot('current_mood')
        mood_intensity = tracker.get_slot('mood_intensity')
        mood_trigger = tracker.get_slot('mood_trigger')

        # Implemente a lógica para salvar ou processar o humor aqui
        # Por exemplo, salvar em um banco de dados ou um arquivo.
        print(f"DEBUG: Humor registrado - Humor: {current_mood}, Intensidade: {mood_intensity}, Gatilho: {mood_trigger}")

        response = f"Seu humor foi registrado: {current_mood} (intensidade {mood_intensity}/10)"
        dispatcher.utter_message(text=response)

        # Se a intensidade for alta, sugere ajuda
        if mood_intensity and int(mood_intensity) >= 7:
            dispatcher.utter_message(response="utter_ask_for_more_help_high_intensity")
        else:
            dispatcher.utter_message(response="utter_ask_for_more_help")

        # Limpar os slots do formulário após o registro
        return [SlotSet("current_mood", None), 
                SlotSet("mood_intensity", None), 
                SlotSet("mood_trigger", None)]


class ActionMoodSummary(Action):
    def name(self) -> Text:
        return "action_mood_summary"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Aqui você implementaria a lógica para recuperar o histórico de humor.
        # Por enquanto, vamos simular um histórico.
        # Em um projeto real, você buscaria isso de um banco de dados.
        mood_history = "Você se sentiu feliz ontem e um pouco estressado hoje cedo."
        
        # Para que o bot possa usar este valor, ele deve ser armazenado em um slot
        # e a resposta `utter_mood_summary` deve estar configurada para usá-lo.
        dispatcher.utter_message(response="utter_mood_summary", mood_history=mood_history)
        
        return [SlotSet("mood_history", mood_history)] # Opcional: Salvar o histórico no slot