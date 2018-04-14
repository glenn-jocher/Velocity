import os, sys, time, cv2, plots
import numpy as np


def annotateImageDF(im, r):
    h, w, ch = im.shape
    n = len(r)
    thick = round(h * .003)

    c = [255, 255, 255]
    for i in range(n):
        a = r[i]
        left, top = a['topleft']['x'], a['topleft']['y']
        right, bot = a['bottomright']['x'], a['bottomright']['y']
        cv2.rectangle(im, (left, top), (right, bot), c, thick + 2)
        cv2.putText(im, 'df %s %.0f%%' % (a['label'], a['confidence'] * 100), (left, top - round(h * .01)),
                    0, 1e-3 * h, c, thick, lineType=cv2.LINE_AA)
    return im


def annotateImageDN(im, r):
    h, w, ch = im.shape
    n = len(r)
    thick = round(h * .003)

    c = [0, 0, 0]  # orange
    for i in range(n):
        a = r[i]
        b = a[2]
        left, top = int(b[0] - b[2] / 2), int(b[1] - b[3] / 2)
        right, bot = int(b[0] + b[2] / 2), int(b[1] + b[3] / 2)
        cv2.rectangle(im, (left, top), (right, bot), c, thick + 2)
        cv2.putText(im, 'dn %s %.0f%%' % (a[0].decode('utf-8'), a[1] * 100), (left, top - round(h * .01)),
                    0, 1e-3 * h, c, thick, lineType=cv2.LINE_AA)
    return im


def mainYOLO():
    PATH = '/Users/glennjocher/darknet/'  # local path to cloned darknet repo
    bPATH = PATH.encode('utf-8')
    sys.path.append(PATH)

    # Darkflow
    from darkflow.net.build import TFNet
    options = {'model': PATH + 'cfg/yolov2-tiny.cfg', 'load': PATH + 'yolov2-tiny.weights', 'threshold': 0.6}
    tfnet = TFNet(options)
    # yolov2.224: 143ms
    # yolov2.320: 240ms
    # yolov2.416: 395ms
    # yolov2-tiny.224: 43ms
    # yolov2-tiny.416: 130ms

    # Darknet
    import darknet as dn
    net = dn.load_net(bPATH + b'cfg/yolov2-tiny.cfg', bPATH + b'yolov2-tiny.weights', 0)
    meta = dn.load_meta(bPATH + b'cfg/coco.data')

    # IMAGE
    # fname = PATH + '../Downloads/IMG_4122.JPG'
    fname = PATH + 'data/dog.jpg'
    im = cv2.imread(fname)  # native BGR

    tic = time.time()
    rf = tfnet.return_predict(im)  # wants BGR
    print('%.3fs darkflow\n%s' % (time.time() - tic, rf))

    tic = time.time()
    rn = dn.detect(net, meta, im)
    print('%.3fs darknet\n%s' % (time.time() - tic, rn))

    im = annotateImageDF(im, rf)
    im = annotateImageDN(im, rn)

    plots.imshow(cv2.cvtColor(im, cv2.COLOR_BGR2RGB))
    cv2.imwrite(fname + '.yolo.jpg', im)
    return

    # VIDEO
    # fname = PATH + '../Downloads/DATA/VSM/2018.3.30/IMG_4238.m4v'
    cap = cv2.VideoCapture(fname)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    nframes = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    out = cv2.VideoWriter(fname + '.yolo.mov', cv2.VideoWriter_fourcc(*'avc1'), fps, (width, height))

    for i in range(30 * 26):
        success, im = cap.read()  # native BGR
        if success:
            tic = time.time()
            rf = tfnet.return_predict(im)  # wants BGR
            print('Frame %g/%g darkflow... %.3fs.' % (i, nframes, time.time() - tic))
            if any(rf): im = annotateImageDF(im, rf)

            # tic = time.time()
            # rn = dn.detect(net, meta, im)
            # print('Frame %g/%g darknet... %.3fs.' % (i, nframes, time.time() - tic))
            # if any(rn): im = annotateImageDN(im, rn)

            out.write(im)  # wants BGR
            # plots.imshow(im)
        else:
            break
    cap.release()
    out.release()

    return None
    # ./darknet detect cfg/yolov3.cfg yolov3.weights /Users/glennjocher/Downloads/IMG_4122.JPG
    # ./darknet detect cfg/yolov2-tiny.cfg yolov2-tiny.weights /Users/glennjocher/Downloads/IMG_4122.JPG


def mainTF():
    tic = time.time()
    import tensorflow as tf
    print('\nimport tensorflow as tf... %.1fs' % (time.time() - tic))

    # What model to download.
    # MODEL_NAME = 'mask_rcnn_inception_v2_coco_2018_01_28'
    # MODEL_NAME = 'faster_rcnn_inception_v2_coco_2018_01_28'
    # MODEL_NAME = 'ssd_inception_v2_coco_2017_11_17'
    MODEL_NAME = 'ssd_mobilenet_v1_coco_2017_11_17'

    tic = time.time()
    PATH = '/Users/glennjocher/'  # local path to cloned darknet repo
    tfPATH = PATH + 'tensorflow/models/research/object_detection/'
    sys.path.append(tfPATH)
    sys.path.append(tfPATH + '..')
    from utils import ops as utils_ops
    from utils import label_map_util
    from utils import visualization_utils as vis_util

    def run_inference(im, T, sess, image_tensor):
        # Run inference
        # I = np.empty((30, im.shape[0], im.shape[1], 3), np.uint8)
        # for i in range(I.shape[0]):
        # I[i] = im
        I = np.expand_dims(im, 0)
        D = sess.run(T, feed_dict={image_tensor: I})

        # all outputs are float32 numpy arrays, so convert types as appropriate
        for key in D:
            D[key] = D[key][0]
        D['num_detections'] = int(D['num_detections'])
        D['detection_classes'] = D['detection_classes'].astype(np.uint8)
        return D

    # Loading label map
    # Label maps map indices to category names, so that when our convolution network predicts `5`, we know that this
    # corresponds to `airplane`.  Here we use internal utility functions, but
    # anything that returns a dictionary mapping integers to appropriate string labels would be fine
    label_map = label_map_util.load_labelmap(tfPATH + 'data/mscoco_label_map.pbtxt')
    categories = label_map_util.convert_label_map_to_categories(label_map, max_num_classes=label_map.__sizeof__(),
                                                                use_display_name=True)
    category_index = label_map_util.create_category_index(categories)

    # Load a (frozen) Tensorflow model into memory.
    graph_def = tf.GraphDef()
    with tf.gfile.GFile(MODEL_NAME + '/frozen_inference_graph.pb', 'rb') as fid:
        serialized_graph = fid.read()
        graph_def.ParseFromString(serialized_graph)
        tf.import_graph_def(graph_def, name='')

    # Get handles to input and output tensors
    ops = tf.get_default_graph().get_operations()
    all_tensor_names = {output.name for op in ops for output in op.outputs}
    T = {}  # tensor dictionary
    for key in ['num_detections', 'detection_boxes', 'detection_scores', 'detection_classes', 'detection_masks']:
        tensor_name = key + ':0'
        if tensor_name in all_tensor_names:
            T[key] = tf.get_default_graph().get_tensor_by_name(tensor_name)
    image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')
    print('Load model into memory... %.1fs' % (time.time() - tic))

    # Start session
    sess = tf.Session()

    # # IMAGES
    # # fname = [os.path.join(tfPATH + 'test_images/', 'image{}.jpg'.format(i)) for i in range(1, 3)]
    # fname = ['/Users/glennjocher/Downloads/taya.jpg', '/Users/glennjocher/Downloads/IMG_4122.JPG']
    # for image_path in fname:
    #     im = cv2.cvtColor(cv2.imread(image_path), cv2.COLOR_BGR2RGB)  # TF wants RGB
    #     U = T.copy()
    #     if 'detection_masks' in U:
    #         # The following processing is only for single im
    #         boxes = tf.squeeze(U['detection_boxes'], 0)
    #         masks = tf.squeeze(U['detection_masks'], 0)
    #         # Reframe is required to translate mask from box coordinates to im coordinates and fit the im size.
    #         j = tf.cast(U['num_detections'][0], tf.int32)
    #         boxes = tf.slice(boxes, [0, 0], [j, -1])
    #         masks = tf.slice(masks, [0, 0, 0], [j, -1, -1])
    #         masks_reframed = utils_ops.reframe_box_masks_to_image_masks(masks, boxes, im.shape[0], im.shape[1])
    #         masks_reframed = tf.cast(tf.greater(masks_reframed, 0.5), tf.uint8)
    #         # Follow the convention by adding back the batch dimension
    #         U['detection_masks'] = tf.expand_dims(masks_reframed, 0)
    #
    #     # Actual detection.
    #     tic = time.time()
    #     D = run_inference(im, U, sess, image_tensor)
    #     print('Inference... %.3fs' % (time.time() - tic))
    #
    #     # Visualization of the results of a detection.
    #     vis_util.visualize_boxes_and_labels_on_image_array(im, D['detection_boxes'], D['detection_classes'],
    #                                                        D['detection_scores'], category_index,
    #                                                        instance_masks=D.get('detection_masks'),
    #                                                        use_normalized_coordinates=True, line_thickness=8)
    #     plots.imshow(im)

    # VIDEO
    fname = PATH + 'Downloads/DATA/VSM/2018.3.30/IMG_4239.m4v'
    cap = cv2.VideoCapture(fname)
    scale = 1 / 1
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) * scale)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) * scale)
    fps = cap.get(cv2.CAP_PROP_FPS)
    nframes = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    out = cv2.VideoWriter(fname + '.junk.mov', cv2.VideoWriter_fourcc(*'avc1'), fps, (width, height))

    mode = 'perframe'
    tic0 = time.time()
    nframes = 120
    if mode == 'chunks':
        # load frames into memory
        tic = time.time()
        IM = np.empty((nframes, height, width, 3), dtype=np.uint8)
        for i in range(nframes):
            success, im = cap.read()  # native BGR
            if success:
                im = cv2.resize(im, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
                IM[i] = im
            else:
                break
        print('Reading %s frames all at once... %.3fs' % (nframes, time.time() - tic))

        # Actual detection.
        tic = time.time()
        D = sess.run(T, feed_dict={image_tensor: np.flip(IM, axis=3)})  # TF wants RGB
        print('Inference... %.3fs.' % (time.time() - tic))
        for j in range(i):
            vis_util.visualize_boxes_and_labels_on_image_array(IM[j], D['detection_boxes'][j],
                                                               D['detection_classes'][j].astype(np.uint8),
                                                               D['detection_scores'][j], category_index,
                                                               instance_masks=D.get('detection_masks'),
                                                               use_normalized_coordinates=True, line_thickness=8)
            out.write(IM[j])  # wants BGR
            # plots.imshow(im)
    else:
        # load frames into memory
        for i in range(nframes):
            success, im = cap.read()  # native BGR
            if success:
                tic = time.time()
                im = cv2.resize(im, (0, 0), fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
                D = sess.run(T, feed_dict={image_tensor: np.expand_dims(cv2.cvtColor(im, cv2.COLOR_BGR2RGB), 0)})
                print('Inference %g/%g... %.3fs.' % (i, nframes, time.time() - tic))
                vis_util.visualize_boxes_and_labels_on_image_array(im, D['detection_boxes'][0],
                                                                   D['detection_classes'][0].astype(np.uint8),
                                                                   D['detection_scores'][0], category_index,
                                                                   use_normalized_coordinates=True, line_thickness=8)
                out.write(im)  # wants BGR
            else:
                break

    print('All done... %.3fs.' % (time.time() - tic0))
    cap.release()
    out.release()

    # Close sess
    sess.close()

mainTF()
