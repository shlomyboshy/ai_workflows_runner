"""
Flow Request Handler - Listens to RabbitMQ queue and executes a workflow
"""
import json
import os
import sys
import logging
import traceback
from typing import Dict, Any

import pika
from pika.exceptions import AMQPConnectionError

from src.workflows_runner import WorkflowRunner


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FlowRequestHandler:

    def __init__(self):
        self.rabbitmq_host = os.environ.get('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = int(os.environ.get('RABBITMQ_PORT', 5672))
        self.rabbitmq_user = os.environ.get('RABBITMQ_USER', 'guest')
        self.rabbitmq_password = os.environ.get('RABBITMQ_PASSWORD', 'guest')
        self.queue_name = os.environ.get('WORKFLOW_QUEUE_NAME', 'workflow_requests')
        self.response_queue_name = os.environ.get('WORKFLOW_RESPONSE_QUEUE_NAME', 'workflow_responses')
        self.connection = None
        self.channel = None
        self.runner = None
        logger.info(f"Initializing FlowRequestHandler for queue: {self.queue_name}")

    def connect_rabbitmq(self):
        try:
            credentials = pika.PlainCredentials(self.rabbitmq_user, self.rabbitmq_password)
            parameters = pika.ConnectionParameters(
                host=self.rabbitmq_host,
                port=self.rabbitmq_port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            self.channel.queue_declare(queue=self.response_queue_name, durable=True)
            self.channel.basic_qos(prefetch_count=1) # Set QoS to process one message at a time
            logger.info(f"Connected to RabbitMQ at {self.rabbitmq_host}:{self.rabbitmq_port}")
            return True
        except AMQPConnectionError as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False

    def load_workflows(self):
        try:
            logger.info("Loading workflow graphs...")
            self.runner = WorkflowRunner()
            logger.info(f"Loaded {len(self.runner.workflow_graphs)} workflows: {list(self.runner.workflow_graphs.keys())}")
            return True
        except Exception as e:
            logger.error(f"Failed to load workflows: {e}")
            logger.error(traceback.format_exc())
            return False

    def process_message(self, ch, method, properties, body):
        request_id = None
        try:
            message = json.loads(body.decode('utf-8'))
            workflow_name = message.get('workflow_name')
            call_transcript = message.get('call_transcript')
            request_id = message.get('request_id', 'unknown')

            logger.info(f"[Request {request_id}] Processing workflow: {workflow_name}")
            if workflow_name not in self.runner.workflow_graphs:
                error_msg = f"Workflow '{workflow_name}' not found. Available: {list(self.runner.workflow_graphs.keys())}"
                logger.error(f"[Request {request_id}] {error_msg}")
                self._send_response(request_id, workflow_name, None, error_msg)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            logger.info(f"[Request {request_id}] Executing workflow with initial state: {call_transcript}")

            initial_state = {"call_transcript": call_transcript}
            result = self.runner.run_flow(workflow_name, initial_state)

            logger.info(f"[Request {request_id}] Workflow completed successfully")
            logger.debug(f"[Request {request_id}] Result: {result}")

            self._send_response(request_id, workflow_name, result, None)
            ch.basic_ack(delivery_tag=method.delivery_tag) # Acknowledge message

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON message: {e}"
            logger.error(f"[Request {request_id}] {error_msg}")
            self._send_response(request_id, "unknown", None, error_msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            error_msg = f"Error processing workflow: {str(e)}\n{traceback.format_exc()}"
            logger.error(f"[Request {request_id}] {error_msg}")
            self._send_response(request_id, message.get('workflow_name', 'unknown'), None, error_msg)
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def _send_response(self, request_id: str, workflow_name: str, result: Dict[str, Any], error: str = None):
        """Send workflow execution response to response queue"""
        try:
            response = {
                "request_id": request_id,
                "workflow_name": workflow_name,
                "success": error is None,
                "result": result,
                "error": error
            }

            self.channel.basic_publish(
                exchange='',
                routing_key=self.response_queue_name,
                body=json.dumps(response),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    content_type='application/json'
                )
            )
            logger.info(f"[Request {request_id}] Response sent to {self.response_queue_name}")

        except Exception as e:
            logger.error(f"Failed to send response: {e}")

    def start_listening(self):
        """Start listening for workflow requests"""
        if not self.connect_rabbitmq():
            logger.error("Failed to connect to RabbitMQ. Exiting.")
            sys.exit(1)

        if not self.load_workflows():
            logger.error("Failed to load workflows. Exiting.")
            sys.exit(1)

        logger.info(f"Starting to consume messages from queue: {self.queue_name}")
        logger.info("Press CTRL+C to stop")

        self.channel.basic_consume(
            queue=self.queue_name,
            on_message_callback=self.process_message
        )

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer...")
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Error in consumer: {e}")
            logger.error(traceback.format_exc())
        finally:
            if self.connection and not self.connection.is_closed:
                self.connection.close()
                logger.info("RabbitMQ connection closed")


def main():
    logger.info("Starting Workflow Request Handler")
    handler = FlowRequestHandler()
    handler.start_listening()


if __name__ == "__main__":
    main()
