// GameplayMessage 실험의 채널과 메시지 구조체 (Docs/UE/GameplayMessage.md).

#include "GameplayMessageLab/GMLabMessages.h"

UE_DEFINE_GAMEPLAY_TAG_COMMENT(TAG_GMLab_Message, "Lab.Message", "GameplayMessage 실험 채널의 부모");
UE_DEFINE_GAMEPLAY_TAG_COMMENT(TAG_GMLab_Message_Damage, "Lab.Message.Damage", "표적이 맞았다");
UE_DEFINE_GAMEPLAY_TAG_COMMENT(TAG_GMLab_Message_Elimination, "Lab.Message.Elimination", "표적이 쓰러졌다");
UE_DEFINE_GAMEPLAY_TAG_COMMENT(TAG_GMLab_Message_Accolade, "Lab.Message.Accolade", "연속 처치 칭호의 부모");
UE_DEFINE_GAMEPLAY_TAG_COMMENT(TAG_GMLab_Message_Accolade_DoubleKill, "Lab.Message.Accolade.DoubleKill", "2연속 처치");
UE_DEFINE_GAMEPLAY_TAG_COMMENT(TAG_GMLab_Message_Accolade_TripleKill, "Lab.Message.Accolade.TripleKill", "3연속 처치");
UE_DEFINE_GAMEPLAY_TAG_COMMENT(TAG_GMLab_Message_Test, "Lab.Message.Test", "호출 순서 실험");
UE_DEFINE_GAMEPLAY_TAG_COMMENT(TAG_GMLab_Bench, "Lab.Bench", "벤치마크 채널. Lab.Message 아래가 아니다");
