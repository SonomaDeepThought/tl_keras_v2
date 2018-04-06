from keras import backend as K
from keras import optimizers
from retrain import create_bottlenecks, cross_validate, \
        load_base_model, train_and_evaluate, group_dict
import report

from keras.models import Model, Sequential
from keras.layers import Dropout, Flatten, Dense, GlobalAveragePooling2D, Input

import numpy as np
import os.path
import shutil
import sys

os.environ["CUDA_VISIBLE_DEVICES"]="0"

def create_groups(data_dir, groups_file):
    """Save csv (file_name,patient) of patient grouping."""

    print("\nCreating patient groups...")
    if not os.path.exists(groups_file):
        # load images
        from keras.preprocessing.image import ImageDataGenerator
        datagen = ImageDataGenerator()
        images = datagen.flow_from_directory(
            data_dir,
            batch_size=1,
            class_mode='categorical',
            shuffle=False)

        file_names = images.filenames

        group = []    
        for name in file_names:
            group.append(name.split('patient')[1][0:-4])

        groups = np.hstack((np.array(file_names).reshape((-1,1)), np.array(group).reshape((-1,1))))
        np.savetxt(groups_file, groups, delimiter=',', fmt='%s')
        print("Done.")
    else:
        print("Patient groups already exist.")

_model = 'inception_v3'

t_layers = []
base_model_str = ''
if _model == 'vgg19' or _model == 'vgg16':
	t_layers = ['block5_pool', 'block4_pool', 'block3_pool']
	if _model == 'vgg19':
		base_model_str = 'VGG19'
	else:
		base_model_str = 'VGG16'
elif _model == 'inception_v3':
	t_layers = ['mixed5']
	base_model_str = 'InceptionV3'
elif _model == 'resnet50':
	t_layers = ['activation_35', 'activation_28', 'activation_21', 'activation_14', 'activation_7']
	base_model_str = 'ResNet50'
elif _model == 'xception':
	t_layers = [
		'block13_sepconv2_act', 'block12_sepconv3_act', 'block11_sepconv3_act', 'block10_sepconv3_act',
		'block9_sepconv3_act', 'block8_sepconv3_act', 'block7_sepconv3_act', 'block6_sepconv3_act',
		'block5_sepconv3_act', 'block4_sepconv2_act', 'block3_sepconv2_act', 'block2_sepconv2_act',
		'block1_sepconv2_act']
	base_model_str = 'Xception'
elif _model == 'inception_resnet_v2':
	t_layers = ['block8_4_mixed', 'block8_2_mixed', 'block17_20_mixed', 'block17_16_mixed', 'block17_12_mixed', 'block17_8_mixed', 'block17_4_mixed']
	base_model_str = 'InceptionResnetV2'


# load base model
input_shape = None
#base_model = load_base_model('InceptionV3', input_shape)
#base_model = load_base_model('ResNet50', input_shape)
#base_model = load_base_model('VGG16')
#base_model = load_base_model('VGG19', input_shape)
#base_model = load_base_model('Xception', input_shape)
#base_model = load_base_model('InceptionResnetV2', input_shape)

	
# extract features from an earlier InceptionV3 layer
#base_model = Model(inputs=base_model.input, outputs=base_model.get_layer('mixed10').output, name='inception_v3')
#base_model = Model(inputs=base_model.input, outputs=base_model.get_layer('avg_pool').output, name='resnet50')
#base_model = Model(input=base_model.input, outputs=base_model.get_layer('block5_pool').output, name='vgg16')
#base_model = Model(input=base_model.input, outputs=base_model.get_layer('block4_conv4').output, name='vgg19')
#base_model = Model(input=base_model.input, outputs=base_model.get_layer('block14_sepconv2_act').output, name='xception')
#base_model = Model(input=base_model.input, outputs=base_model.get_layer('conv_7b_ac').output, name='inception_resnet_v2')
#print(base_model.output.name, "layer will be used for creating bottlenecks.")  
#x = base_model.output
#x = GlobalAveragePooling2D()(x)
#base_model = Model(inputs=base_model.input, outputs=x, name='inception_v3')
#base_model = Model(inputs=base_model.input, outputs=x, name='resnet50')
#base_model = Model(inputs=base_model.input, outputs=x, name='vgg16')
#base_model = Model(inputs=base_model.input, outputs=x, name='vgg19')
#base_model = Model(inputs=base_model.input, outputs=x, name='xception')
#base_model = Model(inputs=base_model.input, outputs=x, name='inception_resnet_v2')
#base_model.summary()

# setup paths
data_dir = '../multi-class2'
tmp_dir = './research/tmp/'
log_dir = tmp_dir + 'logs/'
groups_file = './research/patient-groups.csv' # csv -> file_name,group

# create directories if missing
if os.path.exists(tmp_dir + 'results'):
	shutil.rmtree(tmp_dir + 'results')
os.makedirs(tmp_dir + 'results')
print(tmp_dir + 'results/')

out_file = open('results.txt', 'w')
f1_avgs = {}
f1_stds = {}
cv = True
groups = "patient-groups"
bottleneck_base = './research/tmp/' + _model + '-'
for i in range(len(t_layers)):
	bottleneck_file = ''
	base_model = None
	base_model = load_base_model(base_model_str, input_shape)
	#da_layers = base_model.layers
	#my_layer = base_model.get_layer(t_layers[i])
	#for j in range(len(da_layers)):
	#	dis_layer = da_layers[j]
	#	if dis_layer == my_layer:
	#		print()
	#		print('layer is index ' + str(j))
	#		print()
	base_model = Model(inputs=base_model.input, outputs=base_model.get_layer(t_layers[i]).output, name=_model)
	print(base_model.output.name, "layer will be used for creating bottlenecks.")
	x = base_model.output
	x = GlobalAveragePooling2D()(x)
	base_model = Model(inputs=base_model.input, outputs=x, name=_model)
	bottleneck_file = bottleneck_base + t_layers[i] + '.h5'
	create_groups(data_dir, groups_file)
	print()
	report.data_summary(data_dir, groups_file, csv=tmp_dir+'data_summary.csv')
	groups_files = [groups_file]
	bottlenecks = create_bottlenecks(bottleneck_file, data_dir, base_model, groups_files)
	[f1_avg, f1_std] = cross_validate(
				base_model, bottlenecks, tmp_dir, data_dir, groups=groups,
				num_folds=5, logo=True, use_weights=False, resample=1.0,
				optimizer=None, dropout_rate=0.5, epochs=20, batch_size=512,
				summarize_model=False, summarize_misclassified_images=False)
	f1_avgs[t_layers[i]] = f1_avg
	f1_stds[t_layers[i]] = f1_std
	out_file.write(t_layers[i] + ': ' + str(f1_avg) + ' | ' + str(f1_std) + '\n')
exit()
for key in f1_avgs:
	print('Layer: ' + key + '\n\tAvg F1 Score: ' + str(f1_avgs[key]) + '\n\tStd Dev: ' + str(f1_stds[key]))

exit()

#bottleneck_file = './research/tmp/inception_v3-mixed10.h5'
#bottleneck_file = './research/tmp/resnet50-converted.h5'
#bottleneck_file = './research/tmp/vgg16-converted.h5'
#bottleneck_file = './research/tmp/vgg19-4conv4.h5'
#bottleneck_file = './research/tmp/xception.h5'
#bottleneck_file = './research/tmp/inception_resnet_v2.h5'

# create groups files
#create_groups(data_dir, groups_file)
#print()
#report.data_summary(data_dir, groups_file, csv=tmp_dir+'data_summary.csv')

# get/create bottlenecks 
#groups_files = [groups_file]
#bottlenecks = create_bottlenecks(bottleneck_file, data_dir, base_model, groups_files)

# perform tests
cv = True
groups = "patient-groups"

if not cv:
    train_and_evaluate(
            base_model, bottlenecks, tmp_dir, log_dir, 
            test_size=0.3, groups=groups, use_weights=True,
            optimizer=None, dropout_rate=0.5, epochs=20, batch_size=512,
            save_model=False)
else:
    cross_validate(
            base_model, bottlenecks, tmp_dir, data_dir, groups=groups, 
            num_folds=5, logo=True, use_weights=False, resample=1.0,
            optimizer=None, dropout_rate=0.5, epochs=20, batch_size=512,
            summarize_model=True, summarize_misclassified_images=True)

K.clear_session() # prevent TensorFlow error message

