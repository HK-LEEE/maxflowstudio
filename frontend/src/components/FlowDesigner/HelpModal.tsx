/**
 * Help Modal Component
 * 사용자 가이드 및 도움말을 제공하는 모달
 */

import React from 'react';
import { Modal, Tabs, Typography, Space, Card, Tag, Divider } from 'antd';
import {
  RocketOutlined,
  NodeIndexOutlined,
  ThunderboltOutlined,
  ExperimentOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';

const { Title, Paragraph, Text } = Typography;
const { TabPane } = Tabs;

interface HelpModalProps {
  visible: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<HelpModalProps> = ({ visible, onClose }) => {
  return (
    <Modal
      title={
        <Space>
          <QuestionCircleOutlined />
          <span>FlowStudio 사용 가이드</span>
        </Space>
      }
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
      style={{ top: 20 }}
      bodyStyle={{ maxHeight: 'calc(100vh - 200px)', overflowY: 'auto' }}
    >
      <Tabs defaultActiveKey="start">
        <TabPane 
          tab={
            <Space>
              <RocketOutlined />
              시작하기
            </Space>
          } 
          key="start"
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={4}>🎉 FlowStudio에 오신 것을 환영합니다!</Title>
              <Paragraph>
                FlowStudio는 시각적 프로그래밍을 위한 노드 기반 워크플로우 편집기입니다.
                복잡한 로직을 드래그 앤 드롭으로 쉽게 구성할 수 있습니다.
              </Paragraph>
            </div>

            <div>
              <Title level={5}>📌 기본 개념</Title>
              <Card size="small">
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div>
                    <Text strong>노드 (Node)</Text>
                    <Paragraph style={{ marginBottom: 8 }}>
                      특정 기능을 수행하는 기본 블록입니다. 각 노드는 입력을 받아 처리한 후 결과를 출력합니다.
                    </Paragraph>
                  </div>
                  <div>
                    <Text strong>연결선 (Edge)</Text>
                    <Paragraph style={{ marginBottom: 8 }}>
                      노드 간의 데이터 흐름을 나타냅니다. 출력 포트에서 입력 포트로 연결됩니다.
                    </Paragraph>
                  </div>
                  <div>
                    <Text strong>포트 (Port)</Text>
                    <Paragraph style={{ marginBottom: 0 }}>
                      노드의 입출력 연결점입니다. 왼쪽이 입력, 오른쪽이 출력 포트입니다.
                    </Paragraph>
                  </div>
                </Space>
              </Card>
            </div>

            <div>
              <Title level={5}>🚀 빠른 시작</Title>
              <ol>
                <li>왼쪽 노드 팔레트에서 원하는 노드를 드래그하여 캔버스에 놓습니다</li>
                <li>노드의 출력 포트를 다른 노드의 입력 포트로 드래그하여 연결합니다</li>
                <li>노드를 클릭하여 오른쪽 속성 패널에서 설정을 조정합니다</li>
                <li>상단의 "Test" 버튼으로 워크플로우를 실행해봅니다</li>
                <li>"Save" 버튼으로 작업을 저장합니다</li>
              </ol>
            </div>
          </Space>
        </TabPane>

        <TabPane 
          tab={
            <Space>
              <NodeIndexOutlined />
              노드 가이드
            </Space>
          } 
          key="nodes"
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={4}>📥 입출력 노드</Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card size="small" title="Flow Input" extra={<Tag color="green">시작점</Tag>}>
                  <Paragraph>
                    워크플로우의 시작점입니다. 외부에서 전달받은 데이터를 다음 노드로 전달합니다.
                  </Paragraph>
                  <Text type="secondary">연결 가능: 모든 노드의 입력 포트</Text>
                </Card>
                <Card size="small" title="Flow Output" extra={<Tag color="blue">종료점</Tag>}>
                  <Paragraph>
                    워크플로우의 최종 결과를 반환합니다. 여러 개의 Output 노드를 사용할 수 있습니다.
                  </Paragraph>
                  <Text type="secondary">연결 가능: 모든 노드의 출력 포트</Text>
                </Card>
              </Space>
            </div>

            <Divider />

            <div>
              <Title level={4}>🤖 AI/LLM 노드</Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card size="small" title="OpenAI" extra={<Tag color="purple">GPT 모델</Tag>}>
                  <Paragraph>
                    OpenAI의 ChatGPT 모델을 사용합니다. API 키 설정이 필요합니다.
                  </Paragraph>
                  <Space>
                    <Text type="secondary">입력: 프롬프트, 컨텍스트</Text>
                    <Text type="secondary">출력: AI 응답</Text>
                  </Space>
                </Card>
                <Card size="small" title="Claude" extra={<Tag color="magenta">Anthropic</Tag>}>
                  <Paragraph>
                    Anthropic의 Claude 모델을 사용합니다. 더 안전하고 유용한 응답을 제공합니다.
                  </Paragraph>
                  <Space>
                    <Text type="secondary">입력: 프롬프트, 컨텍스트</Text>
                    <Text type="secondary">출력: AI 응답</Text>
                  </Space>
                </Card>
                <Card size="small" title="Ollama" extra={<Tag color="cyan">로컬 LLM</Tag>}>
                  <Paragraph>
                    로컬에서 실행되는 오픈소스 LLM입니다. 데이터 보안이 중요한 경우 사용합니다.
                  </Paragraph>
                  <Space>
                    <Text type="secondary">입력: 메시지</Text>
                    <Text type="secondary">출력: 로컬 AI 응답</Text>
                  </Space>
                </Card>
              </Space>
            </div>

            <Divider />

            <div>
              <Title level={4}>🔧 로직 & 변환 노드</Title>
              <Space direction="vertical" style={{ width: '100%' }}>
                <Card size="small" title="Template" extra={<Tag color="orange">템플릿</Tag>}>
                  <Paragraph>
                    변수를 활용한 텍스트 템플릿을 생성합니다. {'{Variable1}'} 형식으로 변수를 사용합니다.
                  </Paragraph>
                  <Space>
                    <Text type="secondary">입력: 템플릿, 변수들</Text>
                    <Text type="secondary">출력: 포맷된 텍스트</Text>
                  </Space>
                </Card>
              </Space>
            </div>
          </Space>
        </TabPane>

        <TabPane 
          tab={
            <Space>
              <ThunderboltOutlined />
              단축키
            </Space>
          } 
          key="shortcuts"
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={4}>⌨️ 키보드 단축키</Title>
              <Card>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>Ctrl + C</Text>
                    <Text>선택한 노드 복사</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>Ctrl + V</Text>
                    <Text>노드 붙여넣기</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>Ctrl + S</Text>
                    <Text>워크플로우 저장</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>Ctrl + Z</Text>
                    <Text>실행 취소</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>Ctrl + Y</Text>
                    <Text>다시 실행</Text>
                  </div>
                </Space>
              </Card>
            </div>

            <div>
              <Title level={4}>🖱️ 마우스 조작</Title>
              <Card>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>노드 드래그</Text>
                    <Text>노드 위치 이동</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>빈 공간 드래그</Text>
                    <Text>캔버스 이동</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>마우스 휠</Text>
                    <Text>확대/축소</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>포트 클릭 & 드래그</Text>
                    <Text>노드 연결</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>연결선 더블클릭</Text>
                    <Text>연결 삭제</Text>
                  </div>
                  <Divider style={{ margin: '8px 0' }} />
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <Text strong>노드 ... 메뉴</Text>
                    <Text>노드 옵션 (삭제, 복제 등)</Text>
                  </div>
                </Space>
              </Card>
            </div>
          </Space>
        </TabPane>

        <TabPane 
          tab={
            <Space>
              <ExperimentOutlined />
              예제
            </Space>
          } 
          key="examples"
        >
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div>
              <Title level={4}>💡 간단한 예제</Title>
              
              <Card title="1. 기본 AI 챗봇" style={{ marginBottom: 16 }}>
                <Paragraph>
                  가장 간단한 AI 챗봇 워크플로우입니다.
                </Paragraph>
                <ol>
                  <li><Text code>Flow Input</Text> → <Text code>OpenAI</Text> → <Text code>Flow Output</Text></li>
                  <li>OpenAI 노드에서 모델과 온도 설정</li>
                  <li>Test로 실행하여 채팅 테스트</li>
                </ol>
              </Card>

              <Card title="2. 템플릿 활용 챗봇" style={{ marginBottom: 16 }}>
                <Paragraph>
                  템플릿을 사용하여 일관된 형식의 응답을 생성합니다.
                </Paragraph>
                <ol>
                  <li><Text code>Flow Input</Text> → <Text code>Template</Text> → <Text code>Ollama</Text> → <Text code>Flow Output</Text></li>
                  <li>Template에 "당신은 친절한 상담사입니다. 질문: {'{Variable1}'}"</li>
                  <li>Variable1에 Flow Input 연결</li>
                  <li>Ollama로 로컬에서 처리</li>
                </ol>
              </Card>

              <Card title="3. 다중 AI 비교">
                <Paragraph>
                  여러 AI 모델의 응답을 비교합니다.
                </Paragraph>
                <ol>
                  <li>하나의 <Text code>Flow Input</Text>을 여러 AI 노드에 연결</li>
                  <li><Text code>OpenAI</Text>, <Text code>Claude</Text>, <Text code>Ollama</Text> 병렬 연결</li>
                  <li>각각 별도의 <Text code>Flow Output</Text>으로 출력</li>
                  <li>응답 품질과 속도 비교</li>
                </ol>
              </Card>
            </div>

            <div>
              <Title level={5}>🎯 베스트 프랙티스</Title>
              <ul>
                <li>복잡한 프롬프트는 Template 노드로 관리하세요</li>
                <li>민감한 데이터는 Ollama(로컬 LLM)를 사용하세요</li>
                <li>노드가 많아지면 카테고리별로 정리하여 배치하세요</li>
                <li>자주 사용하는 패턴은 저장하여 재사용하세요</li>
              </ul>
            </div>
          </Space>
        </TabPane>
      </Tabs>
    </Modal>
  );
};